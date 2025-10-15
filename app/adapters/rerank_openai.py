"""OpenAI embedding-based reranker using cosine similarity."""

from __future__ import annotations

import os
import time
from math import ceil
from typing import List, Sequence

import numpy as np
from openai import APIError, OpenAI, RateLimitError

from app.ports import RerankerPort


class OpenAIRerankerAdapter(RerankerPort):
    """Re-rank candidates via OpenAI embeddings scored with cosine similarity."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-large",
        *,
        topn: int | None = 20,
        max_candidates: int | None = None,
        truncate_chars: int = 1200,
        normalize: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 1.5,
    ) -> None:
        self.model = model_name or os.getenv("RERANK_MODEL", "text-embedding-3-large")
        self.topn = max(1, int(topn)) if topn else None
        self.max_candidates = max_candidates if max_candidates is None else max(1, int(max_candidates))
        self.truncate_chars = max(0, int(truncate_chars))
        self.normalize = bool(normalize)
        self.max_retries = max(1, int(max_retries))
        self.retry_backoff = max(0.1, float(retry_backoff))
        self.client = OpenAI()

        self.last_run_ms: float = 0.0
        self.last_batches: int = 0
        self.last_candidates: int = 0

    def _truncate(self, text: str) -> str:
        if self.truncate_chars <= 0 or not text:
            return text
        if len(text) <= self.truncate_chars:
            return text
        truncated = text[: self.truncate_chars]
        last_space = truncated.rfind(" ")
        if last_space > self.truncate_chars // 2:
            truncated = truncated[:last_space]
        return truncated

    def _embed_batch(self, payload: List[str]) -> np.ndarray:
        attempt = 0
        while True:
            try:
                response = self.client.embeddings.create(model=self.model, input=payload)
                return np.asarray([record.embedding for record in response.data], dtype="float32")
            except RateLimitError:  # pragma: no cover - requires live API
                attempt += 1
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff * attempt)
            except APIError as exc:  # pragma: no cover - requires live API
                attempt += 1
                status = getattr(exc, "status_code", None)
                if status == 429 and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * attempt)
                    continue
                raise

    def _prepare_vectors(self, query: str, candidates: Sequence[dict]) -> tuple[np.ndarray, np.ndarray]:
        texts = [self._truncate((hit.get("metadata", {}) or {}).get("preview") or (hit.get("metadata", {}) or {}).get("text") or "") for hit in candidates]
        batch = [query] + texts
        vectors = self._embed_batch(batch)
        q_vec = vectors[0]
        doc_vecs = vectors[1:]
        if self.normalize:
            def _norm(v: np.ndarray) -> np.ndarray:
                norms = np.linalg.norm(v, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return v / norms

            q_vec = _norm(q_vec[np.newaxis, :])[0]
            doc_vecs = _norm(doc_vecs)
        return q_vec, doc_vecs

    def rerank(self, query: str, hits: List[dict]) -> List[dict]:
        if not hits:
            self.last_run_ms = 0.0
            self.last_batches = 0
            self.last_candidates = 0
            return hits

        candidates = hits
        tail: List[dict] = []
        if self.topn and len(candidates) > self.topn:
            candidates = candidates[: self.topn]
            tail = hits[self.topn :]
        if self.max_candidates and len(candidates) > self.max_candidates:
            tail = candidates[self.max_candidates :] + tail
            candidates = candidates[: self.max_candidates]

        start = time.perf_counter()
        q_vec, doc_vecs = self._prepare_vectors(query, candidates)
        scores = doc_vecs @ q_vec
        elapsed = (time.perf_counter() - start) * 1000.0

        self.last_run_ms = float(elapsed)
        self.last_candidates = len(candidates)
        self.last_batches = ceil(len(candidates) / max(1, len(candidates)))  # embeddings endpoint handles batch
        print(
            f"[rerank.openai] pool={len(hits)} scored={self.last_candidates} "
            f"topn={self.topn} truncate={self.truncate_chars} elapsed={self.last_run_ms:.1f}ms"
        )

        reranked: List[dict] = []
        for hit, score in zip(candidates, scores.tolist()):
            if "faiss_score" not in hit and "score" in hit:
                try:
                    hit["faiss_score"] = float(hit["score"])
                except (TypeError, ValueError):
                    hit["faiss_score"] = hit.get("score")
            rerank_val = float(score)
            hit["rerank_score"] = rerank_val
            hit["score"] = rerank_val
            reranked.append(hit)

        reranked.sort(key=lambda item: item.get("rerank_score", item.get("score", 0.0)), reverse=True)
        if tail:
            reranked.extend(tail)
        return reranked
