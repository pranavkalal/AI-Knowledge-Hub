#!/usr/bin/env python
import argparse, numpy as np
from store.store_faiss import FaissFlatIP

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--index_out", default="data/embeddings/vectors.faiss")
    args = ap.parse_args()

    vecs = np.load(args.vecs).astype(np.float32)
    idx = FaissFlatIP(vecs.shape[1])
    idx.add(vecs)
    idx.save(args.index_out)
    print({"added": int(vecs.shape[0]), "dim": int(vecs.shape[1]), "index": args.index_out})

if __name__ == "__main__":
    main()
