import faiss
import numpy as np
from typing import List, Dict, Optional, Tuple

class FaissStore:
    def __init__(self, dim: int, use_cosine: bool = True):
        self.dim = dim
        self.use_cosine = use_cosine
        # Use ID map so doc IDs aren’t tied to list order
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))  # IP + IDs
        self.docs: Dict[int, Dict] = {}
        self._next_id = 0

    @staticmethod
    def _as_f32(a: np.ndarray) -> np.ndarray:
        return np.ascontiguousarray(np.asarray(a, dtype="float32"))

    @staticmethod
    def _safe_normalize(a: np.ndarray) -> None:
        # Avoid division by zero inside normalize_L2
        norms = np.linalg.norm(a, axis=1 if a.ndim == 2 else 0)
        if np.any(norms == 0):
            raise ValueError("Zero‑norm vector encountered; check your embeddings.")
        faiss.normalize_L2(a)

    def index_docs(self, embeddings: np.ndarray, docs: List[Dict]) -> None:
        emb = self._as_f32(embeddings)
        if emb.ndim != 2 or emb.shape[1] != self.dim:
            raise ValueError(f"Embeddings must be [n, {self.dim}], got {emb.shape}")
        if len(docs) != emb.shape[0]:
            raise ValueError("docs length must match number of embeddings.")
        if self.use_cosine:
            self._safe_normalize(emb)

        # Assign stable int IDs
        ids = np.arange(self._next_id, self._next_id + emb.shape[0], dtype="int64")
        self.index.add_with_ids(emb, ids)
        for i, d in zip(ids.tolist(), docs):
            self.docs[i] = d
        self._next_id += emb.shape[0]

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        if self.index.ntotal == 0:
            return []
        q = self._as_f32(query_embedding)[None, :]
        if q.shape[1] != self.dim:
            raise ValueError(f"Query must have dim {self.dim}, got {q.shape[1]}")
        if self.use_cosine:
            self._safe_normalize(q)

        k = min(top_k, self.index.ntotal)
        D, I = self.index.search(q, k)  # D: scores, I: ids
        results = []
        for rank, (doc_id, score) in enumerate(zip(I[0], D[0]), 1):
            if doc_id == -1:
                continue
            d = self.docs.get(int(doc_id), {})
            results.append({
                "rank": rank,
                "id": int(doc_id),
                "score": float(score),
                "doc": d,
            })
        return results

    def save(self, path: str) -> None:
        faiss.write_index(self.index, f"{path}/index.faiss")
        # Save docs map
        import json, os
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/docs.jsonl", "w", encoding="utf-8") as f:
            for k, v in self.docs.items():
                f.write(json.dumps({"id": k, "doc": v}) + "\n")

    def load(self, path: str) -> None:
        import json
        self.index = faiss.read_index(f"{path}/index.faiss")
        # If the saved index wasn’t IDMap2, wrap it
        if not isinstance(self.index, faiss.IndexIDMap2):
            self.index = faiss.IndexIDMap2(self.index)
        self.docs.clear()
        with open(f"{path}/docs.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                self.docs[int(row["id"])] = row["doc"]
        self._next_id = (max(self.docs.keys()) + 1) if self.docs else 0

    def search_batch(self, query_embeddings: np.ndarray, top_k: int = 5
                     ) -> List[List[Dict]]:
        Q = self._as_f32(query_embeddings)
        if Q.ndim != 2 or Q.shape[1] != self.dim:
            raise ValueError(f"Queries must be [m, {self.dim}], got {Q.shape}")
        if self.use_cosine:
            self._safe_normalize(Q)
        if self.index.ntotal == 0:
            return [[] for _ in range(Q.shape[0])]

        k = min(top_k, self.index.ntotal)
        D, I = self.index.search(Q, k)
        out = []
        for d_row, i_row in zip(D, I):
            row = []
            for rank, (doc_id, score) in enumerate(zip(i_row, d_row), 1):
                if doc_id == -1:
                    continue
                row.append({
                    "rank": rank,
                    "id": int(doc_id),
                    "score": float(score),
                    "doc": self.docs.get(int(doc_id), {}),
                })
            out.append(row)
        return out
