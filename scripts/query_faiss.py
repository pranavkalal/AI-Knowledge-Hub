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

Example:
  >>> python scripts/query_faiss.py --q "irrigation" --no-show-titles
  #1 score=0.842 id=DOC_chunk0001
"""

import argparse
import json
import numpy as np
from collections import defaultdict

# Unified embedding path: same as API
from app.adapters.embed_bge import BGEEmbeddingAdapter
from app.services.formatting import format_citation, format_metadata, format_snippet
from store.store_faiss import FaissFlatIP
from rag.retrieval.utils import (
    neighbor_ids,
    load_lookup,
    passes_filters,
    stitch_preview,
)


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
    ap.add_argument(
        "--show-titles",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include title/year/page metadata in pretty output (use --no-show-titles for minimal lines)",
    )
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
            hit = {
                "score": float(score),
                "metadata": {
                    **rec,
                    "preview": preview,
                },
            }
            payload = format_citation(hit)
            payload.update({
                "id": cid,
                "score": round(score, 3),
            })
            if args.show_counts:
                w, c, t = maybe_counts(preview)
                payload["preview_words"] = w
                payload["preview_chars"] = c
                if t is not None:
                    payload["preview_tokens"] = t
            print(json.dumps(payload, ensure_ascii=False))
        return

    for rank, (score, cid, rec) in enumerate(results, 1):
        prev = stitch_preview(
            rec, lookup,
            neighbors=args.neighbors,
            max_chars=args.max_preview_chars,
            no_truncate=args.no_truncate
        )
        snippet = format_snippet(prev or "", length=180)
        meta_suffix = format_metadata(rec)
        title = rec.get("title") or rec.get("doc_id") or "?"
        header = f"{rank:>2} {score:.3f}  {title}"
        if meta_suffix:
            header = f"{header} {meta_suffix}"
        print(f"{header}  {snippet}")

        if args.show_counts:
            w, c, t = maybe_counts(prev)
            tok_str = f", tokens~{t}" if t is not None else ""
            print(f"   counts: {w} words, {c} chars{tok_str}")
        if not args.show_titles:
            print(f"   text:  {prev}\n")


if __name__ == "__main__":
    main()
