"""
Adapter for FAISS vector store that wraps store/store_faiss.py FaissFlatIP.
Implements VectorStorePort and reads ids.npy + chunks.jsonl for metadata.
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Mapping
import numpy as np
import json
from functools import lru_cache
from app.ports import VectorStorePort
from store.store_faiss import FaissFlatIP


class FaissStoreAdapter(VectorStorePort):
    def __init__(
        self,
        index_path: str,
        ids_path: str,
        meta_path: str = "data/staging/chunks.jsonl", # Kept for signature compatibility
        embed_model: Optional[str] = None,
        embed_config: Optional[Mapping[str, object]] = None,
    ):
        # Load your wrapper class (not the raw faiss index)
        self.ff = FaissFlatIP.load(index_path)
        self.ids = np.load(ids_path, allow_pickle=True)
        # self.meta_path = meta_path # Unused now
        self._embed_model = embed_model or os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5")
        self._embedder = None
        self._embed_config: Dict[str, object] = dict(embed_config or {})
        self._embed_config.setdefault("model", self._embed_model)
        adapter = self._embed_config.get("adapter") or os.environ.get("EMB_ADAPTER")
        if adapter:
            self._embed_config["adapter"] = adapter

    def get_meta_map(self) -> dict:
        """Expose cached metadata for downstream utilities. 
        DEPRECATED: Returns empty dict to force on-demand fetch."""
        return {}

    def get_metadata(self, chunk_id: str) -> dict | None:
        """Return metadata for a specific chunk id."""
        from rag.store.sqlite_store import get_chunk_by_id
        return get_chunk_by_id(chunk_id)

    def get_metadata_batch(self, chunk_ids: List[str]) -> Dict[str, Dict]:
        """Return metadata for multiple chunk ids."""
        from rag.store.sqlite_store import get_chunks_batch
        return get_chunks_batch(chunk_ids)

    @lru_cache(maxsize=1)
    def _ensure_embedder(self):
        from app.adapters.loader import load_embedder

        return load_embedder(self._embed_config, os.environ)

    def add(self, ids: List[str], vectors: List[List[float]], metadatas: List[Dict]):
        # Index is built offline via scripts/build_faiss.py
        return

    def query(self, query_vector: List[float], k: int) -> List[Dict]:
        q = np.array(query_vector, dtype="float32")[None, :]
        D, I = self.ff.search(q, k)
        
        # Get IDs of hits
        hit_ids = []
        hit_scores = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            hit_ids.append(self.ids[idx])
            hit_scores.append(float(score))
            
        # Fetch metadata from SQLite
        from rag.store.sqlite_store import get_chunks_batch
        meta_map = get_chunks_batch(hit_ids)
        
        hits = []
        for chunk_id, score in zip(hit_ids, hit_scores):
            md = meta_map.get(chunk_id, {})
            hits.append({
                "id": chunk_id,
                "score": score,
                "faiss_score": score,
                "metadata": md,
            })
        return hits

    def search_raw(self, query: str, top_k: int = 10) -> List[Dict]:
        """Embed the query text and return the top chunks using FAISS search."""
        emb = self._ensure_embedder()
        qvec = emb.embed_query(query)
        return self.query(qvec, top_k)
