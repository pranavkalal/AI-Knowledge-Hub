
"""Callback handlers for LangChain tracing/logging."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Sequence

from langchain.callbacks.base import BaseCallbackHandler


class LoggingCallbackHandler(BaseCallbackHandler):
    """Stream basic retrieval/LLM telemetry to stdout for debugging."""

    def __init__(self):
        self._retriever_start: float | None = None
        self._last_query: str | None = None
        self._chain_start: float | None = None

    def _now(self) -> str:
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def on_chain_start(self, *args, **kwargs):
        self._chain_start = time.perf_counter()

    def on_retriever_start(self, *args, **kwargs):
        query = kwargs.get("query")
        if query is None and args:
            query = args[0]
        query = query or "<unknown>"
        self._retriever_start = time.perf_counter()
        self._last_query = str(query)
        print(f"[{self._now()}] retriever:start query={query!r}")

    def on_retriever_end(self, *args, **kwargs):
        documents = kwargs.get("documents")
        if documents is None and args:
            documents = args[0]
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

    def on_chain_end(self, outputs: Any, **kwargs):
        timeline = []
        if isinstance(outputs, dict):
            timeline = outputs.get("timings") or []

        stage_totals: Dict[str, float] = {}
        stage_order: List[str] = []
        for entry in timeline:
            stage = str(entry.get("stage"))
            seconds = float(entry.get("seconds") or 0.0)
            if stage not in stage_totals:
                stage_totals[stage] = 0.0
                stage_order.append(stage)
            stage_totals[stage] += seconds

        summary_parts = [f"{stage}={stage_totals[stage]:.3f}s" for stage in stage_order]
        total_from_timeline = sum(stage_totals.values())

        total_elapsed = None
        if self._chain_start is not None:
            total_elapsed = time.perf_counter() - self._chain_start
        self._chain_start = None

        total = total_from_timeline if total_from_timeline > 0 else (total_elapsed or 0.0)

        summary = " ".join(summary_parts) if summary_parts else "completed"
        print(f"[{self._now()}] chain:end {summary} total={total:.3f}s")
