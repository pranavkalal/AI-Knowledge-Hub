"""
Adapter that produces embeddings via the OpenAI Embeddings API.

Inputs
------
texts : list[str]
    Raw text passages or queries to embed. Empty/blank strings are skipped by
    the caller; this adapter assumes non-empty inputs.

Outputs
-------
list[list[float]]
    Dense vector representations (float32) with optional L2 normalisation so
    they can drop into the existing FAISS + cosine similarity pipeline.

The adapter relies on `OPENAI_API_KEY` (and optional org/project env vars) being
available to `openai.OpenAI()`. Model defaults can be overridden via the
`EMB_MODEL` environment variable or the runtime configuration passed into the
factory.
"""

from __future__ import annotations

import os
import time
from typing import Iterable, List, Sequence

import numpy as np
from openai import APIError, OpenAI, RateLimitError

from app.ports import EmbedderPort


class OpenAIEmbeddingAdapter(EmbedderPort):
    """Embed texts using OpenAI's Embeddings API with basic retry handling."""

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int = 128,
        normalize: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 1.5,
    ) -> None:
        self.model_name = model_name or os.getenv("EMB_MODEL", "text-embedding-3-small")
        self.batch_size = max(1, int(batch_size))
        self.normalize = bool(normalize)
        self.max_retries = max(1, int(max_retries))
        self.retry_backoff = max(0.1, float(retry_backoff))
        self.client = OpenAI()

    def _request_embeddings(self, chunk: Sequence[str]) -> List[List[float]]:
        attempt = 0
        while True:
            try:
                response = self.client.embeddings.create(model=self.model_name, input=list(chunk))
                return [record.embedding for record in response.data]
            except RateLimitError as exc:  # pragma: no cover - requires live API
                attempt += 1
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff * attempt)
            except APIError as exc:  # pragma: no cover - requires live API
                status = getattr(exc, "status_code", None)
                attempt += 1
                if status == 429 and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    continue
                raise

    def _iter_batches(self, texts: Sequence[str]) -> Iterable[Sequence[str]]:
        for start in range(0, len(texts), self.batch_size):
            yield texts[start : start + self.batch_size]

    def _maybe_normalize(self, vectors: np.ndarray) -> np.ndarray:
        if not self.normalize:
            return vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for batch in self._iter_batches(texts):
            if not batch:
                continue
            batch_vecs = self._request_embeddings(batch)
            vectors.extend(batch_vecs)
        if not vectors:
            return []
        arr = np.asarray(vectors, dtype="float32")
        arr = self._maybe_normalize(arr)
        return arr.astype("float32").tolist()

    def embed_query(self, text: str) -> List[float]:
        result = self.embed_texts([text])
        return result[0] if result else []
