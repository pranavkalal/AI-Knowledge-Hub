"""
Cross-encoder reranker using BAAI/bge-reranker-base from Hugging Face.
Scores (query, passage) pairs and sorts descending. Big quality boost for citations.
"""

from __future__ import annotations

from math import ceil
from time import perf_counter
from typing import List, Sequence

import torch
from app.ports import RerankerPort
from sentence_transformers import CrossEncoder


class BGERerankerAdapter(RerankerPort):
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        *,
        topn: int | None = 20,
        batch_size: int = 16,
        max_length: int = 256,
        device: str | None = None,
    ):
        self.topn = max(1, int(topn)) if topn else None
        self.batch_size = max(1, int(batch_size))
        self.max_length = max(8, int(max_length))
        self.device = device
        self.ce = CrossEncoder(model_name, device=device)
        if hasattr(self.ce, "model"):
            self.ce.model.eval()
        self.last_run_ms: float = 0.0
        self.last_batches: int = 0
        self.last_candidates: int = 0
        # Rough char budget for reranker input (controls cost, independent of LLM prompt)
        self._max_input_chars = self.max_length * 4

    def _truncate_for_rerank(self, text: str) -> str:
        if not text:
            return ""
        if len(text) <= self._max_input_chars:
            return text
        truncated = text[: self._max_input_chars]
        last_space = truncated.rfind(" ")
        if last_space > self._max_input_chars // 2:
            truncated = truncated[:last_space]
        return truncated

    def _prepare_pairs(self, query: str, hits: Sequence[dict]) -> List[tuple[str, str]]:
        pairs: List[tuple[str, str]] = []
        for h in hits:
            meta = h.get("metadata", {}) if isinstance(h, dict) else {}
            text = meta.get("preview") or meta.get("text") or ""
            pairs.append((query, self._truncate_for_rerank(text)))
        return pairs

    def rerank(self, query: str, hits: List[dict]) -> List[dict]:
        if not hits:
            self.last_run_ms = 0.0
            self.last_batches = 0
            self.last_candidates = 0
            return hits

        candidates = hits
        tail: List[dict] = []
        if self.topn and len(hits) > self.topn:
            candidates = hits[: self.topn]
            tail = hits[self.topn :]

        pairs = self._prepare_pairs(query, candidates)
        start = perf_counter()
        with torch.inference_mode():
            scores = (
                self.ce.predict(
                    pairs,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    max_length=self.max_length,
                )
                .tolist()
            )

        elapsed = (perf_counter() - start) * 1000.0
        self.last_run_ms = elapsed
        self.last_batches = ceil(len(pairs) / self.batch_size) if pairs else 0
        self.last_candidates = len(pairs)

        reranked: List[dict] = []
        for h, score in zip(candidates, scores):
            if "faiss_score" not in h and "score" in h:
                try:
                    h["faiss_score"] = float(h["score"])
                except (TypeError, ValueError):
                    h["faiss_score"] = h.get("score")
            rerank_value = float(score)
            h["rerank_score"] = rerank_value
            h["score"] = rerank_value
            reranked.append(h)

        print(
            f"[reranker] candidates={self.last_candidates} batch_size={self.batch_size} "
            f"rerank_batches={self.last_batches} time={self.last_run_ms:.1f}ms"
        )

        reranked.sort(key=lambda x: x.get("rerank_score", x.get("score", 0.0)), reverse=True)
        if tail:
            reranked.extend(tail)
        return reranked
