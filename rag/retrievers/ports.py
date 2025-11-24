from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import PrivateAttr

from rag.retrieval.utils import prepare_hits, resolve_retrieval_settings
from rag.retrieval.pdf_links import enrich_metadata


class PortsRetriever(BaseRetriever):
    """
    LangChain retriever built on top of the VectorStorePort implementation.
    """

    class Config:
        arbitrary_types_allowed = True

    top_k: int = 10
    neighbors: int = 1
    contains: Optional[List[str]] = None
    year_range: Optional[Tuple[int, int]] = None
    diversify_per_doc: bool = True

    _store: Any = PrivateAttr()
    _contains: List[str] = PrivateAttr(default_factory=list)
    _year_range: Optional[Tuple[int, int]] = PrivateAttr(default=None)
    _base_filters: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _candidate_limit: int = PrivateAttr(default=0)
    _last_candidates: int = PrivateAttr(default=0)
    _last_overfetch: int = PrivateAttr(default=0)
    _overfetch_factor: float = PrivateAttr(default=1.6)

    def __init__(
        self,
        store: Any,
        top_k: int = 10,
        neighbors: int = 1,
        contains: Optional[List[str]] = None,
        year_range: Optional[Tuple[int, int]] = None,
        diversify_per_doc: bool = True,
        candidate_overfetch_factor: float = 1.6,
    ):
        super().__init__(
            top_k=top_k,
            neighbors=neighbors,
            contains=contains,
            year_range=year_range,
            diversify_per_doc=diversify_per_doc,
        )

        object.__setattr__(self, "top_k", max(1, self.top_k))
        object.__setattr__(self, "neighbors", max(0, self.neighbors))
        object.__setattr__(self, "diversify_per_doc", bool(self.diversify_per_doc))

        self._store = store

        normalized_contains: List[str] = []
        for kw in (self.contains or []):
            text = str(kw).strip().lower()
            if text and text not in normalized_contains:
                normalized_contains.append(text)
        self._contains = normalized_contains

        year_bounds: Optional[Tuple[int, int]] = None
        if self.year_range:
            ymin, ymax = self.year_range
            try:
                ymin = int(ymin) if ymin is not None else None
            except (TypeError, ValueError):
                ymin = None
            try:
                ymax = int(ymax) if ymax is not None else None
            except (TypeError, ValueError):
                ymax = None
            if ymin is not None and ymax is not None and ymin > ymax:
                ymin, ymax = ymax, ymin
            if ymin is not None or ymax is not None:
                year_bounds = (ymin, ymax)
        self._year_range = year_bounds

        base_filters: Dict[str, Any] = {}
        if self._contains:
            base_filters["contains"] = list(self._contains)
        if self._year_range:
            ymin, ymax = self._year_range
            if ymin is not None:
                base_filters["year_min"] = ymin
            if ymax is not None:
                base_filters["year_max"] = ymax
        base_filters["neighbors"] = self.neighbors
        base_filters["per_doc"] = 1 if self.diversify_per_doc else 0
        base_filters["diversify_per_doc"] = bool(self.diversify_per_doc)
        object.__setattr__(self, "_base_filters", base_filters)
        object.__setattr__(self, "_candidate_limit", int(self.top_k))
        object.__setattr__(self, "_last_candidates", 0)
        object.__setattr__(self, "_last_overfetch", 0)
        try:
            overfetch_factor = float(candidate_overfetch_factor)
        except (TypeError, ValueError):
            overfetch_factor = 1.6
        if overfetch_factor <= 0:
            overfetch_factor = 1.6
        object.__setattr__(self, "_overfetch_factor", overfetch_factor)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _coerce_payload(query: Any) -> Dict[str, Any]:
        if isinstance(query, dict):
            return query
        return {"question": query}

    def _merge_filters(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        filters: Dict[str, Any] = dict(self._base_filters)

        raw_filters = payload.get("filters")
        if hasattr(raw_filters, "model_dump"):
            try:
                raw_filters = raw_filters.model_dump(exclude_none=True)
            except Exception:
                raw_filters = raw_filters.model_dump()
        if isinstance(raw_filters, dict):
            for key, value in raw_filters.items():
                if value is None or value == "":
                    continue
                filters[key] = value

        for key in (
            "contains",
            "year_min",
            "year_max",
            "neighbors",
            "per_doc",
            "max_preview_chars",
            "max_snippet_chars",
            "diversify_per_doc",
        ):
            value = payload.get(key)
            if value is None or value == "":
                continue
            filters[key] = value

        filters.setdefault("max_preview_chars", 2400)
        filters.setdefault("max_snippet_chars", 1400)

        return filters

    def _resolve_top_k(self, payload: Dict[str, Any]) -> int:
        top_k = self.top_k
        raw = payload.get("k")
        if raw is not None:
            try:
                top_k = max(1, int(raw))
            except (TypeError, ValueError):
                pass
        return top_k

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        """Support LangChain's Runnable interface."""
        return self._get_relevant_documents(input)

    async def ainvoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        return self._get_relevant_documents(input)

    # ---------------------------------------------------------------- retrieval
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        payload = self._coerce_payload(query)
        question = str(payload.get("question") or "").strip()
        if not question:
            return []
        if not hasattr(self._store, "search_raw"):
            raise RuntimeError("Vector store does not implement search_raw(query, top_k=...).")

        top_k = max(1, self._resolve_top_k(payload))
        candidate_limit = self._candidate_limit or top_k
        candidate_limit_raw = payload.get("candidate_limit")
        if candidate_limit_raw is not None:
            try:
                candidate_limit = int(candidate_limit_raw)
            except (TypeError, ValueError):
                candidate_limit = self._candidate_limit or top_k
        if candidate_limit <= 0:
            candidate_limit = self._candidate_limit or top_k
        candidate_limit = max(candidate_limit, top_k)
        object.__setattr__(self, "_candidate_limit", candidate_limit)

        overfetch_factor = payload.get("candidate_overfetch_factor")
        if overfetch_factor is None:
            overfetch_factor_val = float(self._overfetch_factor or 1.6)
        else:
            try:
                overfetch_factor_val = float(overfetch_factor)
            except (TypeError, ValueError):
                overfetch_factor_val = float(self._overfetch_factor or 1.6)
        if overfetch_factor_val <= 0:
            overfetch_factor_val = float(self._overfetch_factor or 1.6)
        object.__setattr__(self, "_overfetch_factor", overfetch_factor_val)

        filters = self._merge_filters(payload)
        settings = resolve_retrieval_settings(filters)

        ann_start = perf_counter()
        overfetch = int(max(candidate_limit, top_k * 2, candidate_limit * overfetch_factor_val, 32))
        raw_hits = self._store.search_raw(question, top_k=overfetch)
        ann_ms = (perf_counter() - ann_start) * 1000.0

        prepare_start = perf_counter()
        processed_hits = prepare_hits(raw_hits, self._store, settings, limit=candidate_limit)
        prepare_ms = (perf_counter() - prepare_start) * 1000.0

        docs: List[Document] = []
        for hit in processed_hits:
            metadata = dict(hit.get("metadata", {}) if isinstance(hit, dict) else {})
            text = metadata.get("preview") or metadata.get("text") or ""
            metadata.setdefault("preview", text)
            metadata.setdefault("text", text)
            metadata.setdefault("score", hit.get("score", metadata.get("score")))
            metadata.setdefault("faiss_score", hit.get("faiss_score"))
            if hit.get("rerank_score") is not None:
                metadata.setdefault("rerank_score", hit.get("rerank_score"))
            docs.append(Document(page_content=text, metadata=metadata))

        total_ms = ann_ms + prepare_ms
        summary = {
            "ann_ms": ann_ms,
            "stitch_ms": prepare_ms,
            "total_ms": total_ms,
            "candidate_count": len(processed_hits),
            "candidate_limit": candidate_limit,
            "overfetch": overfetch,
        }
        object.__setattr__(self, "_last_timing", summary)
        object.__setattr__(self, "_last_candidates", len(processed_hits))
        object.__setattr__(self, "_last_overfetch", overfetch)

        return docs
