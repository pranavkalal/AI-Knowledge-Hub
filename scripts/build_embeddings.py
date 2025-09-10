#!/usr/bin/env python
import argparse, numpy as np, pandas as pd
from pathlib import Path
from rag.embed.embedder import Embedder

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="data/staging/chunks.jsonl")
    ap.add_argument("--out_vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--out_ids", default="data/embeddings/ids.npy")
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    args = ap.parse_args()

    Path("data/embeddings").mkdir(parents=True, exist_ok=True)

    texts, ids = [], []
    with open(args.chunks, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = __import__("json").loads(line)
            t = rec.get("text", "").strip()
            if not t:
                continue
            texts.append(t)
            ids.append(str(rec["id"]))

    emb = Embedder(args.model).encode(texts)
    np.save(args.out_vecs, emb)
    np.save(args.out_ids, np.array(ids, dtype=object))
    print({"n_chunks": len(ids), "dim": int(emb.shape[1])})

if __name__ == "__main__":
    main()
