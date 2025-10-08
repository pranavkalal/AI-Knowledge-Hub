#!/usr/bin/env python
"""
Build dense embeddings for chunked documents using the same adapter used by the API.
Inputs:
  - JSONL chunks file with records containing at least: { "id": str, "text": str }
Outputs:
  - NumPy arrays: embeddings.npy (float32), ids.npy (object)
Keeps API and batch pipeline aligned via BGEEmbeddingAdapter.
"""

import argparse
import json
from pathlib import Path
import numpy as np

# Use the same adapter the API uses
from app.adapters.embed_bge import BGEEmbeddingAdapter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="data/staging/chunks.jsonl")
    ap.add_argument("--out_vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--out_ids", default="data/embeddings/ids.npy")
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()

    Path(args.out_vecs).parent.mkdir(parents=True, exist_ok=True)

    texts, ids = [], []
    with open(args.chunks, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            t = (rec.get("text") or "").strip()
            cid = str(rec.get("id"))
            if not t or not cid:
                continue
            texts.append(t)
            ids.append(cid)

    if not texts:
        raise SystemExit("No chunks with text found. Check your chunks.jsonl.")

    emb = BGEEmbeddingAdapter(args.model)
    # SentenceTransformers does its own batching; we keep a flag here for future adapters
    vecs = np.asarray(emb.embed_texts(texts), dtype="float32")

    np.save(args.out_vecs, vecs)
    np.save(args.out_ids, np.array(ids, dtype=object))

    print({"n_chunks": len(ids), "dim": int(vecs.shape[1]), "out_vecs": args.out_vecs, "out_ids": args.out_ids})

if __name__ == "__main__":
    main()
