from __future__ import annotations
import numpy as np
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", max_len: int = 512):
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = max_len

    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = True,
    ) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=show_progress_bar,
        ).astype(np.float32)
