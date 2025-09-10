#!/usr/bin/env python
import argparse, json, numpy as np
from collections import defaultdict
from rag.embed.embedder import Embedder
from store.store_faiss import FaissFlatIP

def neighbor_ids(cid: str, neighbors: int) -> list[str]:
    # expects ids like "..._chunk0123"
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

# def stitch_preview(center_rec, lookup, neighbors=1, max_chars=900) -> str:
#     cid = center_rec.get("id", "")
#     parts = []
#     for nid in neighbor_ids(cid, neighbors):
#         rec = lookup.get(nid)
#         if rec and rec.get("text"):
#             parts.append(rec["text"])
#     joined = " ".join(parts) if parts else (center_rec.get("text") or "")
#     return joined[:max_chars].replace("\n", " ")
def stitch_preview(center_rec, lookup, neighbors=1, max_chars=900) -> str:
    cid = center_rec.get("id", "")
    center_doc = center_rec.get("doc_id") or cid.split("_chunk")[0]
    parts = []
    for nid in neighbor_ids(cid, neighbors):
        rec = lookup.get(nid)
        # only stitch if it's the same document
        if rec and (rec.get("doc_id") or nid.split("_chunk")[0]) == center_doc:
            txt = rec.get("text") or ""
            if txt:
                parts.append(txt)
    joined = " ".join(parts) if parts else (center_rec.get("text") or "")
    return joined[:max_chars].replace("\n", " ")


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
    args = ap.parse_args()

    # 1) search with some overfetch to allow filtering/diversification
    idx = FaissFlatIP.load(args.index)
    ids = np.load(args.ids, allow_pickle=True)
    qvec = Embedder().encode([args.q])
    overfetch = max(args.k * 5, 50)
    D, I = idx.search(qvec, k=overfetch)

    # 2) build set of needed ids including neighbors for stitching
    cand_ids = [ids[i] for i in I[0]]
    neighbor_set = set()
    for cid in cand_ids:
        neighbor_set.update(neighbor_ids(cid, args.neighbors))

    # 3) load only those records
    lookup = load_lookup(args.chunks, neighbor_set)

    # 4) collect candidates with filters
    contains_any = [s.strip().lower() for s in args.contains.split(",") if s.strip()] if args.contains else []
    candidates = []
    for score, i in zip(D[0], I[0]):
        cid = ids[i]
        rec = lookup.get(cid)
        if not rec:
            continue
        if not passes_filters(rec, contains_any, args.year_min, args.year_max):
            continue
        candidates.append((float(score), cid, rec))

    # 5) diversify per doc
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

    # 6) output
    if args.json:
        for score, cid, rec in results:
            out = {
                "score": round(score, 3),
                "id": cid,
                "doc_id": rec.get("doc_id"),
                "title": rec.get("title"),
                "year": rec.get("year"),
                "preview": stitch_preview(rec, lookup, neighbors=args.neighbors, max_chars=900),
            }
            print(json.dumps(out, ensure_ascii=False))
        return

    for rank, (score, cid, rec) in enumerate(results, 1):
        print(f"#{rank} score={score:.3f} id={cid}")
        print(f"   title: {rec.get('title') or rec.get('doc_id') or '?'}")
        print(f"   year:  {rec.get('year', '?')}")
        prev = stitch_preview(rec, lookup, neighbors=args.neighbors, max_chars=900)
        print(f"   text:  {prev}\n")

if __name__ == "__main__":
    main()
