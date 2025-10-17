"""
Adapter for embeddings that wraps the existing rag/embed/embedder.py Embedder class.
Implements the EmbedderPort interface so it can be swapped easily with other embedders.
"""

from typing import List

from app.ports import EmbedderPort
from rag.embed.embedder import Embedder


class BGEEmbeddingAdapter(EmbedderPort):
    """Embed texts with SentenceTransformer BGE models."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 64,
        normalize: bool = True,
        show_progress: bool = True,
    ):
        self.embedder = Embedder(model_name)
        self.batch_size = batch_size
        self.normalize = normalize
        self.show_progress = show_progress

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts into dense vectors."""
        enc = self.embedder.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=self.show_progress,
        )
        return enc.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text into a dense vector."""
        return self.embed_texts([text])[0]
