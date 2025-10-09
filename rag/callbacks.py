
"""Callback handlers for LangChain tracing/logging."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, List, Sequence

from langchain.callbacks.base import BaseCallbackHandler


class LoggingCallbackHandler(BaseCallbackHandler):
    """Stream basic retrieval/LLM telemetry to stdout for debugging."""

    def __init__(self):
        self._retriever_start: float | None = None
        self._last_query: str | None = None

    def _now(self) -> str:
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def on_retriever_start(self, *_, query: str, **__):
        self._retriever_start = time.perf_counter()
        self._last_query = query
        print(f"[{self._now()}] retriever:start query={query!r}")

    def on_retriever_end(self, *_, documents: Sequence[Any] | None, **__):
        elapsed = None
        if self._retriever_start is not None:
            elapsed = time.perf_counter() - self._retriever_start
        doc_ids: List[str] = []
        for doc in documents or []:
            meta = getattr(doc, "metadata", {}) or {}
            doc_ids.append(meta.get("doc_id") or meta.get("id") or "<unknown>")
        print(
            f"[{self._now()}] retriever:end docs={doc_ids}"
            + (f" elapsed={elapsed:.3f}s" if elapsed is not None else "")
        )

    def on_llm_end(self, *_, response: Any, **__):
        usage = getattr(response, 'usage', {}) or {}
        print(
            f"[{self._now()}] llm:end prompt_tokens={usage.get('prompt_tokens')}"
            f" completion_tokens={usage.get('completion_tokens')}"
        )
