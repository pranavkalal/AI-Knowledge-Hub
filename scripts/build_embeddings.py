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

# Embedding adapters
from app.adapters.embed_bge import BGEEmbeddingAdapter

try:  # optional dependency
    from app.adapters.embed_openai import OpenAIEmbeddingAdapter
except Exception:  # pragma: no cover - optional env
    OpenAIEmbeddingAdapter = None


def create_embedder(adapter_name: str, model: str, batch: int, normalize: bool):
    key = (adapter_name or "bge").lower()
    if key in {"bge", "bge_local"}:
        return BGEEmbeddingAdapter(model_name=model, batch_size=batch, normalize=normalize)
    if key in {"openai", "openai_embeddings"}:
        if OpenAIEmbeddingAdapter is None:
            raise RuntimeError(
                "OpenAIEmbeddingAdapter not available. Ensure OpenAI dependencies are installed."
            )
        return OpenAIEmbeddingAdapter(model_name=model, batch_size=batch, normalize=normalize)
    raise ValueError(f"Unknown embedding adapter: {adapter_name}")

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

    embedder = create_embedder(args.adapter, args.model, args.batch, args.normalize)
    vecs = np.asarray(embedder.embed_texts(texts), dtype="float32")

    np.save(args.out_vecs, vecs)
    np.save(args.out_ids, np.array(ids, dtype=object))

    print({"n_chunks": len(ids), "dim": int(vecs.shape[1]), "out_vecs": args.out_vecs, "out_ids": args.out_ids})

if __name__ == "__main__":
    main()
