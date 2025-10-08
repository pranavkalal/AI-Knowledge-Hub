#!/usr/bin/env python
"""
Feature-rich FAISS query CLI that matches the API stack.
- Uses the same embedding adapter as /api/ask (BGEEmbeddingAdapter) so results are consistent.
- Preserves your existing goodies: overfetch + per-doc diversification, neighbor stitching,
  keyword/year filters, preview word/char/token counts, JSON/pretty output.

Inputs:
  - FAISS index: data/embeddings/vectors.faiss
  - IDs array:   data/embeddings/ids.npy
  - Chunk meta:  data/staging/chunks.jsonl  (records with keys: id, doc_id, title, year, text, page?, url?)

Usage:
  python scripts/query_faiss.py --q "irrigation efficiency 2018" --k 8 --neighbors 1 --per-doc 2 --show-counts
"""

import argparse
import json
import numpy as np
from collections import defaultdict

# Unified embedding path: same as API
from app.adapters.embed_bge import BGEEmbeddingAdapter
from store.store_faiss import FaissFlatIP


def neighbor_ids(cid: str, neighbors: int) -> list[str]:
    """Return list of neighbor chunk ids ±N around cid (expects suffix `_chunkNNNN`)."""
    if neighbors <= 0:
        return [cid]
    base, _, tail = cid.partition("_chunk")
    try:
        idx = int(tail)
    except ValueError:
        return [cid]
    ids = []
    for j in range(idx - neighbors, idx + neighbors + 1):
        ids.append(f"{base}_chunk{j:04d}")
    return ids


def load_lookup(chunks_path: str, needed_ids: set[str]) -> dict[str, dict]:
    """Read only the chunk records we actually need into a dict keyed by id."""
    lookup = {}
    if not needed_ids:
        return lookup
    with open(chunks_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = rec.get("id")
            if cid in needed_ids:
                lookup[cid] = rec
                if len(lookup) == len(needed_ids):
                    break
    return lookup


def passes_filters(rec, contains_any, year_min, year_max):
    """Apply keyword and year range filters to a chunk record."""
    if contains_any:
        text = (rec.get("text") or "").lower()
        if not any(kw in text for kw in contains_any):
            return False
    y = rec.get("year")
    if year_min is not None and isinstance(y, int) and y < year_min:
        return False
    if year_max is not None and isinstance(y, int) and y > year_max:
        return False
    return True


def stitch_preview(center_rec, lookup, neighbors=1, max_chars=1800, no_truncate=False) -> str:
    """
    Stitch ±neighbors chunks from the same doc to form a readable preview.
    Honors max_chars unless no_truncate=True.
    """
    cid = center_rec.get("id", "")
    center_doc = center_rec.get("doc_id") or cid.split("_chunk")[0]
    parts = []
    total_len = 0

    for nid in neighbor_ids(cid, neighbors):
        rec = lookup.get(nid)
        if rec and (rec.get("doc_id") or nid.split("_chunk")[0]) == center_doc:
            txt = (rec.get("text") or "").replace("\n", " ")
            if not txt:
                continue
            if no_truncate:
                parts.append(txt)
                continue
            room = max_chars - total_len
            if room <= 0:
                break
            if len(txt) <= room:
                parts.append(txt)
                total_len += len(txt)
            else:
                parts.append(txt[:room])
                total_len += room
                break

    joined = " ".join(parts) if parts else (center_rec.get("text") or "")
    return joined if no_truncate else joined[:max_chars]


def maybe_counts(s: str):
    """Return (words, chars, tokens?) using cl100k_base if available."""
    words = len(s.split())
    chars = len(s)
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tok = len(enc.encode(s))
    except Exception:
        tok = None
    return words, chars, tok


def main():
    ap = argparse.ArgumentParser(description="Query FAISS index")
    ap.add_argument("--index", default="data/embeddings/vectors.faiss")
    ap.add_argument("--ids", default="data/embeddings/ids.npy")
    ap.add_argument("--chunks", default="data/staging/chunks.jsonl")
    ap.add_argument("--q", required=True, help="query text")
    ap.add_argument("--k", type=int, default=10, help="top-k to output after diversification")
    ap.add_argument("--per-doc", type=int, default=2, help="max results per document")
    ap.add_argument("--neighbors", type=int, default=1, help="adjacent chunks to stitch for preview")
    ap.add_argument("--contains", default="", help="comma-separated keywords that must appear in chunk text")
    ap.add_argument("--year-min", type=int)
    ap.add_argument("--year-max", type=int)
    ap.add_argument("--json", action="store_true", help="output JSON lines instead of pretty text")
    ap.add_argument("--max-preview-chars", type=int, default=1800, help="char cap for printed preview")
    ap.add_argument("--no-truncate", action="store_true", help="print full stitched preview (ignore char cap)")
    ap.add_argument("--show-counts", action="store_true", help="print word/char/token counts for previews")
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5", help="embedding model (kept for parity with API)")
    args = ap.parse_args()

    # 1) Load FAISS index and ids
    idx = FaissFlatIP.load(args.index)
    # Some versions might return a tuple; be tolerant.
    if isinstance(idx, tuple):
        idx = idx[0]
    ids = np.load(args.ids, allow_pickle=True)

    # 2) Embed query using the same adapter as API
    emb = BGEEmbeddingAdapter(args.model)
    qvec1d = np.array(emb.embed_query(args.q), dtype="float32")
    qvec = qvec1d[None, :]  # shape [1, D]

    # 3) Overfetch to allow filtering and per-doc diversification
    overfetch = max(args.k * 5, 50)
    D, I = idx.search(qvec, k=overfetch)

    # 4) Build neighbor set for stitching and load just those records
    cand_ids = [ids[i] for i in I[0] if i >= 0]
    neighbor_set = set()
    for cid in cand_ids:
        neighbor_set.update(neighbor_ids(cid, args.neighbors))
    lookup = load_lookup(args.chunks, neighbor_set)

    # 5) Apply filters
    contains_any = [s.strip().lower() for s in args.contains.split(",") if s.strip()] if args.contains else []
    candidates = []
    for score, i in zip(D[0], I[0]):
        if i < 0:
            continue
        cid = ids[i]
        rec = lookup.get(cid)
        if not rec:
            continue
        if not passes_filters(rec, contains_any, args.year_min, args.year_max):
            continue
        candidates.append((float(score), cid, rec))

    # 6) Per-doc diversification
    per_doc_count = defaultdict(int)
    results = []
    for score, cid, rec in candidates:
        doc = rec.get("doc_id") or cid.split("_chunk")[0]
        if per_doc_count[doc] >= max(1, args.per_doc):
            continue
        per_doc_count[doc] += 1
        results.append((score, cid, rec))
        if len(results) >= args.k:
            break

    # 7) Output
    if args.json:
        for score, cid, rec in results:
            preview = stitch_preview(
                rec, lookup,
                neighbors=args.neighbors,
                max_chars=args.max_preview_chars,
                no_truncate=args.no_truncate
            )
            out = {
                "score": round(score, 3),
                "id": cid,
                "doc_id": rec.get("doc_id"),
                "title": rec.get("title"),
                "year": rec.get("year"),
                "preview": preview,
            }
            if args.show_counts:
                w, c, t = maybe_counts(preview)
                out["preview_words"] = w
                out["preview_chars"] = c
                if t is not None:
                    out["preview_tokens"] = t
            print(json.dumps(out, ensure_ascii=False))
        return

    for rank, (score, cid, rec) in enumerate(results, 1):
        prev = stitch_preview(
            rec, lookup,
            neighbors=args.neighbors,
            max_chars=args.max_preview_chars,
            no_truncate=args.no_truncate
        )
        title = rec.get("title") or rec.get("doc_id") or "?"
        year = rec.get("year")
        year_str = str(year) if year is not None else "?"
        page = rec.get("page")
        page_str = str(page) if page is not None else "-"
        snippet = (prev or "").replace("\n", " ").strip()
        snippet = snippet[:180]
        print(f"{rank:>2} {score:.3f}  {title} ({year_str})  p{page_str}  {snippet}...")
        if args.show_counts:
            w, c, t = maybe_counts(prev)
            tok_str = f", tokens~{t}" if t is not None else ""
            print(f"   counts: {w} words, {c} chars{tok_str}")
        print()


if __name__ == "__main__":
    main()
