from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.pydantic_v1 import PrivateAttr

from rag.retrieval.utils import neighbor_ids
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

    def __init__(
        self,
        store: Any,
        top_k: int = 10,
        neighbors: int = 1,
        contains: Optional[List[str]] = None,
        year_range: Optional[Tuple[int, int]] = None,
        diversify_per_doc: bool = True,
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

    # ------------------------------------------------------------------ helpers
    def _meta_map(self) -> Dict[str, Dict]:
        if hasattr(self._store, "get_meta_map"):
            try:
                return dict(self._store.get_meta_map())
            except Exception:
                return {}
        return {}

    def _fetch_meta(self, chunk_id: str, cache: Dict[str, Dict]) -> Optional[Dict]:
        rec = cache.get(chunk_id)
        if rec is None and hasattr(self._store, "get_metadata"):
            try:
                rec = self._store.get_metadata(chunk_id)
            except Exception:
                rec = None
            if rec:
                cache[chunk_id] = rec
        return rec

    def _within_year_range(self, year_val: Any) -> bool:
        if self._year_range is None:
            return True
        ymin, ymax = self._year_range
        try:
            year_int = int(year_val)
        except (TypeError, ValueError):
            return False
        if ymin is not None and year_int < ymin:
            return False
        if ymax is not None and year_int > ymax:
            return False
        return True

    def _contains_match(self, text: str) -> bool:
        if not self._contains:
            return True
        source = (text or "").lower()
        return any(kw in source for kw in self._contains)

    def _stitch(
        self,
        center_id: str,
        doc_id: str,
        cache: Dict[str, Dict],
    ) -> Tuple[str, List[int], Optional[Any]]:
        chunk_indices: set[int] = set()
        parts: List[str] = []
        pages: set[Any] = set()

        for nid in neighbor_ids(center_id, self.neighbors):
            rec = self._fetch_meta(nid, cache)
            if rec is None:
                continue
            n_doc = rec.get("doc_id") or nid.split("_chunk")[0]
            if n_doc != doc_id:
                continue

            content = rec.get("text") or rec.get("preview") or ""
            if content:
                parts.append(content.strip())

            idx = rec.get("chunk_index")
            if idx is None:
                tail = nid.split("_chunk")[-1]
                try:
                    idx = int(tail)
                except (TypeError, ValueError):
                    idx = None
            if idx is not None:
                chunk_indices.add(int(idx))

            page = rec.get("page")
            if page not in (None, ""):
                pages.add(page)

        stitched = "\n\n".join(parts).strip()
        sorted_indices = sorted(chunk_indices)

        if not pages:
            page_value: Optional[Any] = None
        elif len(pages) == 1:
            page_value = next(iter(pages))
        else:
            page_value = sorted(pages)

        return stitched, sorted_indices, page_value

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        """Support LangChain's Runnable interface."""
        return self._get_relevant_documents(input)

    async def ainvoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        return self._get_relevant_documents(input)

    # ---------------------------------------------------------------- retrieval
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        question = query["question"] if isinstance(query, dict) else query
        if not hasattr(self._store, "search_raw"):
            raise RuntimeError("Vector store does not implement search_raw(query, top_k=...).")

        raw_hits = self._store.search_raw(question, top_k=self.top_k * 3)
        cache = self._meta_map()
        docs: List[Document] = []
        per_doc_counts: Dict[str, int] = {}

        for hit in raw_hits:
            meta = hit.get("metadata", {}) if isinstance(hit, dict) else {}
            chunk_id = meta.get("id") or hit.get("id")
            if not chunk_id:
                continue

            rec = self._fetch_meta(chunk_id, cache) or meta
            doc_id = rec.get("doc_id") or chunk_id.split("_chunk")[0]
            title = rec.get("title") or meta.get("title") or doc_id
            year_val = rec.get("year") or meta.get("year")
            if not self._within_year_range(year_val):
                continue

            base_text = rec.get("text") or rec.get("preview") or meta.get("text") or ""
            if not self._contains_match(base_text):
                continue

            stitched, chunk_indices, page_value = self._stitch(chunk_id, doc_id, cache)
            if not stitched:
                continue

            if self.diversify_per_doc:
                count = per_doc_counts.get(doc_id, 0)
                if count >= 1:
                    continue
                per_doc_counts[doc_id] = count + 1

            try:
                score = float(hit.get("score", 0.0))
            except Exception:
                score = 0.0

            metadata = {
                "doc_id": doc_id,
                "title": title,
                "year": year_val,
                "page": page_value,
                "chunk_indices": chunk_indices,
                "score": score,
            }
            metadata = enrich_metadata(metadata)
            docs.append(Document(page_content=stitched, metadata=metadata))

            if len(docs) >= self.top_k:
                break

        return docs


class RerankDecoratorRetriever(BaseRetriever):
    """Apply the configured reranker on top of another retriever."""

    class Config:
        arbitrary_types_allowed = True

    base: BaseRetriever
    reranker: Any

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        docs = self.base.get_relevant_documents(query)
        hits = []
        for d in docs:
            md = dict(d.metadata)
            md["text"] = d.page_content
            md.setdefault("preview", d.page_content)
            hits.append({"score": md.get("score"), "metadata": md})

        try:
            reranked = self.reranker.rerank(
                query if isinstance(query, str) else query.get("question", ""),
                hits,
            )
        except Exception:
            reranked = hits

        out: List[Document] = []
        for h in reranked:
            md = dict(h["metadata"])
            text = md.pop("text", "") or md.get("preview", "")
            md["score"] = h.get("score")
            md = enrich_metadata(md)
            out.append(Document(page_content=text, metadata=md))
        return out
