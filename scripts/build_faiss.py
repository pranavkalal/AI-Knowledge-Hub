#!/usr/bin/env python
"""
Build or update a FAISS index from precomputed embeddings.
Inputs:
  - embeddings.npy (float32) shaped [N, D]
Outputs:
  - vectors.faiss FAISS index file
  - optional manifest JSON describing index metadata
Supports incremental updates and configurable FAISS factories.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import faiss  # type: ignore
import numpy as np

from store.store_faiss import FaissFlatIP


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {
            "ids": [],
            "dim": None,
            "created": datetime.utcnow().isoformat(),
            "faiss": {},
        }

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        data = {"ids": [str(x) for x in data]}

    ids = [str(x) for x in data.get("ids", [])]
    data["ids"] = ids
    data.setdefault("dim", None)
    data.setdefault("created", datetime.utcnow().isoformat())
    data.setdefault("faiss", {})
    return data


def _save_manifest(path: Path, manifest: dict) -> None:
    manifest["timestamp"] = datetime.utcnow().isoformat()
    manifest["count"] = len(manifest.get("ids", []))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def _metric_name(metric_val: int) -> str:
    mapping = {
        getattr(faiss, "METRIC_INNER_PRODUCT", None): "inner_product",
        getattr(faiss, "METRIC_L2", None): "l2",
    }
    return mapping.get(metric_val, str(metric_val))


def _maybe_train_index(index, vecs: np.ndarray, rng: np.random.Generator) -> bool:
    if not hasattr(index, "is_trained") or index.is_trained:
        return False

    nlist = getattr(index, "nlist", 0)
    base_train = max(10000, nlist * 40) if nlist else 10000
    train_size = min(vecs.shape[0], base_train)
    if train_size <= 0:
        raise SystemExit("Not enough vectors to train the requested FAISS index.")

    if train_size < vecs.shape[0]:
        sample_idx = rng.choice(vecs.shape[0], train_size, replace=False)
        train_vecs = vecs[sample_idx]
    else:
        train_vecs = vecs
    index.train(train_vecs)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vecs", default="data/embeddings/embeddings.npy")
    ap.add_argument("--ids", default="data/embeddings/ids.npy")
    ap.add_argument("--index_out", default="data/embeddings/vectors.faiss")
    ap.add_argument("--index_in", default=None, help="Optional existing index to update (defaults to --index_out)")
    ap.add_argument(
        "--manifest",
        default=None,
        help="Manifest path (defaults to <index_out>.manifest.json)",
    )
    ap.add_argument(
        "--factory",
        default=None,
        help="FAISS factory string (e.g. IVF4096,Flat). Default: Flat inner-product index.",
    )
    ap.add_argument(
        "--incremental",
        action="store_true",
        help="Append only unseen IDs to an existing index instead of rebuilding from scratch.",
    )
    ap.add_argument(
        "--model",
        default=None,
        help="Embedding model name recorded in the manifest (defaults to EMB_MODEL env or 'unknown').",
    )
    args = ap.parse_args()

    vecs = np.load(args.vecs).astype(np.float32, copy=False)
    if vecs.ndim != 2:
        raise SystemExit(f"Expected 2D embeddings array, got shape {vecs.shape}")

    ids_path = Path(args.ids)
    ids_array = np.load(ids_path, allow_pickle=True)
    if ids_array.shape[0] != vecs.shape[0]:
        raise SystemExit(
            f"ids.npy length {ids_array.shape[0]} does not match embeddings rows {vecs.shape[0]}"
        )

    index_out_path = Path(args.index_out)
    manifest_path = Path(args.manifest) if args.manifest else index_out_path.with_suffix(
        index_out_path.suffix + ".manifest.json"
    )
    manifest = _load_manifest(manifest_path)

    index_in_path = Path(args.index_in) if args.index_in else index_out_path
    incremental = bool(args.incremental and index_in_path.exists())

    rng = np.random.default_rng(0)
    factory_str = (args.factory or "").strip()
    metric_type = getattr(faiss, "METRIC_INNER_PRODUCT", 0)
    embedding_model = (
        args.model
        or os.environ.get("EMB_MODEL")
        or manifest.get("embedding_model")
        or "unknown"
    )

    if incremental:
        idx = FaissFlatIP.load(index_in_path)
        dim_existing = idx.index.d  # type: ignore[attr-defined]
        if dim_existing != vecs.shape[1]:
            raise SystemExit(f"Existing index dim {dim_existing} != embeddings dim {vecs.shape[1]}")

        existing_factory = manifest.get("faiss", {}).get("factory")
        factory_label = factory_str or existing_factory or "Flat"
        if factory_str and existing_factory and factory_str != existing_factory:
            raise SystemExit(
                f"Factory mismatch: existing index uses '{existing_factory}', but --factory '{factory_str}' was provided."
            )

        manifest["faiss"] = {
            "factory": factory_label,
            "metric": _metric_name(getattr(idx.index, "metric_type", metric_type)),
            "trained": bool(getattr(idx.index, "is_trained", True)),
        }
        manifest["dim"] = manifest.get("dim") or dim_existing
        manifest["embedding_model"] = embedding_model

        seen = set(manifest.get("ids", []))
        new_positions = [i for i, cid in enumerate(ids_array) if str(cid) not in seen]
        if not new_positions:
            np.save(ids_path, np.array(manifest["ids"], dtype=object))
            _save_manifest(manifest_path, manifest)
            print(
                {
                    "added": 0,
                    "dim": manifest["dim"],
                    "index": str(index_out_path),
                    "note": "no new ids detected; manifest already up-to-date",
                }
            )
            return

        if hasattr(idx.index, "is_trained") and not idx.index.is_trained:
            raise SystemExit("Existing index is untrained; rebuild without --incremental to initialise it.")

        new_vecs = vecs[new_positions].astype(np.float32, copy=False)
        new_ids = [str(ids_array[i]) for i in new_positions]

        start = idx.index.ntotal  # type: ignore[attr-defined]
        faiss_ids = np.arange(start, start + len(new_vecs), dtype="int64")
        try:
            idx.index.add_with_ids(new_vecs, faiss_ids)  # type: ignore[attr-defined]
        except (AttributeError, RuntimeError):
            idx.add(new_vecs)

        manifest["ids"].extend(new_ids)
        added = len(new_vecs)
    else:
        idx = FaissFlatIP(vecs.shape[1])
        if factory_str:
            idx.index = faiss.index_factory(vecs.shape[1], factory_str, metric_type)
        factory_label = factory_str or "Flat"

        _maybe_train_index(idx.index, vecs, rng)

        faiss_ids = np.arange(vecs.shape[0], dtype="int64")
        try:
            idx.index.add_with_ids(vecs, faiss_ids)  # type: ignore[attr-defined]
        except (AttributeError, RuntimeError):
            idx.add(vecs)

        manifest["ids"] = [str(x) for x in ids_array.tolist()]
        manifest["dim"] = int(vecs.shape[1])
        manifest.setdefault("created", manifest.get("created") or datetime.utcnow().isoformat())
        manifest["embedding_model"] = embedding_model
        manifest["faiss"] = {
            "factory": factory_label,
            "metric": _metric_name(getattr(idx.index, "metric_type", metric_type)),
            "trained": bool(getattr(idx.index, "is_trained", True)),
        }
        added = vecs.shape[0]

    index_out_path.parent.mkdir(parents=True, exist_ok=True)
    idx.save(index_out_path)

    np.save(ids_path, np.array(manifest["ids"], dtype=object))
    _save_manifest(manifest_path, manifest)

    print(
        {
            "added": int(added),
            "total": int(len(manifest["ids"])),
            "dim": int(manifest.get("dim") or vecs.shape[1]),
            "index": str(index_out_path),
            "manifest": str(manifest_path),
            "factory": manifest.get("faiss", {}).get("factory", "Flat"),
        }
    )


if __name__ == "__main__":
    main()
