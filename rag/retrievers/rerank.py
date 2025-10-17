from __future__ import annotations

from typing import Any, List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from rag.retrieval.pdf_links import enrich_metadata


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
            base_score = md.get("score")
            faiss_score = md.get("faiss_score", base_score)
            hit_payload = {
                "score": base_score,
                "faiss_score": faiss_score,
                "metadata": md,
            }
            hits.append(hit_payload)

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
            faiss_score = h.get("faiss_score", md.get("faiss_score"))
            rerank_score = h.get("rerank_score")
            if faiss_score is not None:
                md["faiss_score"] = faiss_score
            if rerank_score is not None:
                md["rerank_score"] = rerank_score
                md["score"] = rerank_score
            else:
                md["score"] = h.get("score")
            md = enrich_metadata(md)
            out.append(Document(page_content=text, metadata=md))
        return out
