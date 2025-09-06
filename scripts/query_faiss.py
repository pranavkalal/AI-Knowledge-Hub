#!/usr/bin/env python
import argparse, numpy as np, pandas as pd
from rag.embed.embedder import Embedder
from store.store_faiss import FaissFlatIP

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="data/embeddings/vectors.faiss")
    ap.add_argument("--ids", default="data/embeddings/ids.npy")
    ap.add_argument("--chunks", default="data/staging/chunks.jsonl")
    ap.add_argument("--q", required=True)
    args = ap.parse_args()

    idx = FaissFlatIP.load(args.index)
    ids = np.load(args.ids, allow_pickle=True)

    qvec = Embedder().encode([args.q])
    D, I = idx.search(qvec, k=5)

    # lazy map back to text
    idset = set(ids[I[0]])
    lookup = {}
    import json
    with open(args.chunks, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["id"] in idset:
                lookup[rec["id"]] = rec

    for rank, (score, i) in enumerate(zip(D[0], I[0]), 1):
        cid = ids[i]
        rec = lookup.get(cid, {})
        title = rec.get("title") or rec.get("doc_id") or "?"
        year = rec.get("year", "?")
        text = (rec.get("text") or "")[:300].replace("\n", " ")
        print(f"#{rank} score={score:.3f} id={cid} title={title} year={year}")
        print(text, "\n")

if __name__ == "__main__":
    main()
