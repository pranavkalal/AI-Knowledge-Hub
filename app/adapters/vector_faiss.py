"""
Adapter for FAISS vector store that wraps store/store_faiss.py FaissFlatIP.
Implements VectorStorePort and reads ids.npy + chunks.jsonl for metadata.
"""

from typing import List, Dict
import numpy as np
import json
from app.ports import VectorStorePort
from store.store_faiss import FaissFlatIP

class FaissStoreAdapter(VectorStorePort):
    def __init__(self, index_path: str, ids_path: str, meta_path: str = "data/staging/chunks.jsonl"):
        # Load your wrapper class (not the raw faiss index)
        self.ff = FaissFlatIP.load(index_path)
        self.ids = np.load(ids_path, allow_pickle=True)
        self.meta_path = meta_path
        self._meta = None

    def _load_meta(self) -> dict:
        if self._meta is None:
            self._meta = {}
            with open(self.meta_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    cid = rec.get("id")
                    if cid:
                        self._meta[cid] = rec
        return self._meta

    def add(self, ids: List[str], vectors: List[List[float]], metadatas: List[Dict]):
        # Index is built offline via scripts/build_faiss.py
        return

    def query(self, query_vector: List[float], k: int) -> List[Dict]:
        q = np.array(query_vector, dtype="float32")[None, :]
        D, I = self.ff.search(q, k)
        meta = self._load_meta()
        hits = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            chunk_id = self.ids[idx]
            md = meta.get(chunk_id, {})
            hits.append({"id": chunk_id, "score": float(score), "metadata": md})
        return hits
