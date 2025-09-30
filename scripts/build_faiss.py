#!/usr/bin/env python
"""
Build a FAISS FlatIP index from precomputed embeddings using the same class used by the API.
Inputs:
  - embeddings.npy (float32) shaped [N, D]
Outputs:
  - vectors.faiss FAISS index file
Does not add metadata; ids live in ids.npy and are loaded at query time by the adapter.
"""

import argparse
import numpy as np
from pathlib import Path
from store.store_faiss import FaissFlatIP

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--index_out", default="data/embeddings/vectors.faiss")
    args = ap.parse_args()

    vecs = np.load(args.vecs).astype(np.float32)
    if vecs.ndim != 2:
        raise SystemExit(f"Expected 2D embeddings array, got shape {vecs.shape}")

    idx = FaissFlatIP(vecs.shape[1])
    idx.add(vecs)

    Path(args.index_out).parent.mkdir(parents=True, exist_ok=True)
    idx.save(args.index_out)

    print({"added": int(vecs.shape[0]), "dim": int(vecs.shape[1]), "index": args.index_out})

if __name__ == "__main__":
    main()
