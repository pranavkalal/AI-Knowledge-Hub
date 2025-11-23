#!/usr/bin/env python
"""
Build dense embeddings for chunked documents using the same adapter used by the API.
Inputs:
  - JSONL chunks file with records containing at least: { "id": str, "text": str }
Outputs:
  - NumPy arrays: embeddings.npy (float32), ids.npy (object)

Supports both the local BGE SentenceTransformer and OpenAI's hosted embeddings so the
batch pipeline stays aligned with runtime configuration.
"""

import argparse
import json
import os
from pathlib import Path
import numpy as np
from dotenv import load_dotenv

# Load env vars (API keys)
load_dotenv()

from app.adapters.loader import load_embedder


def _infer_existing_dim(path: Path) -> int | None:
    if not path.exists():
        return None
    arr = None
    try:
        arr = np.load(path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[0] > 0:
            return int(arr.shape[1])
    except Exception:
        return None
    finally:
        if arr is not None:
            del arr
    return None


def _infer_faiss_dim(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        import faiss  # type: ignore
    except Exception:
        return None
    try:
        idx = faiss.read_index(str(path))
        return int(idx.d)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="data/staging/chunks.jsonl")
    ap.add_argument("--out_vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--out_ids", default="data/embeddings/ids.npy")
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--adapter", default=os.getenv("EMB_ADAPTER", "bge"))
    ap.add_argument("--normalize", dest="normalize", action="store_true")
    ap.add_argument("--no-normalize", dest="normalize", action="store_false")
    ap.set_defaults(normalize=True)
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

    embedder_cfg = {
        "adapter": args.adapter,
        "model": args.model,
        "batch_size": args.batch,
        "normalize": args.normalize,
    }
    embedder = load_embedder(embedder_cfg)

    existing_dims = {}
    prev_dim = _infer_existing_dim(Path(args.out_vecs))
    if prev_dim is not None:
        existing_dims["previous embeddings"] = prev_dim
    faiss_dim = _infer_faiss_dim(Path(args.out_vecs).parent / "vectors.faiss")
    if faiss_dim is not None:
        existing_dims["current FAISS index"] = faiss_dim

    vecs = np.asarray(embedder.embed_texts(texts), dtype="float32")
    new_dim = int(vecs.shape[1]) if vecs.ndim == 2 else None

    if existing_dims and new_dim is not None:
        mismatched = {label: dim for label, dim in existing_dims.items() if dim != new_dim}
        if mismatched:
            details = ", ".join(f"{label}={dim}" for label, dim in mismatched.items())
            print(
                f"[warn] Embedding dimension changed to {new_dim}. Previous artifacts ({details}) differ. "
                "Rebuild the FAISS index via `invoke faiss` or run `invoke build` before serving queries."
            )

    np.save(args.out_vecs, vecs)
    np.save(args.out_ids, np.array(ids, dtype=object))

    print({"n_chunks": len(ids), "dim": int(vecs.shape[1]), "out_vecs": args.out_vecs, "out_ids": args.out_ids})

if __name__ == "__main__":
    main()
