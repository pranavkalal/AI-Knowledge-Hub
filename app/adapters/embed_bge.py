"""
Adapter for embeddings that wraps the existing rag/embed/embedder.py Embedder class.
Implements the EmbedderPort interface so it can be swapped easily with other embedders.
"""

from typing import List
from app.ports import EmbedderPort
from rag.embed.embedder import Embedder  # your existing class

class BGEEmbeddingAdapter(EmbedderPort):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.embedder = Embedder(model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts into dense vectors."""
        return self.embedder.encode(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text into a dense vector."""
        return self.embedder.encode([text])[0].tolist()
