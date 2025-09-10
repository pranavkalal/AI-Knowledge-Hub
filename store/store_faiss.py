from __future__ import annotations
import faiss
import numpy as np
from pathlib import Path
from typing import Tuple

class FaissFlatIP:
    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)

    def add(self, vectors: np.ndarray):
        self.index.add(vectors.astype(np.float32))

    def search(self, qvecs: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        return self.index.search(qvecs.astype(np.float32), k)

    def save(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    @classmethod
    def load(cls, path: str | Path):
        idx = faiss.read_index(str(path))
        obj = cls(idx.d)
        obj.index = idx
        return obj
