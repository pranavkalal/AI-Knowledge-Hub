# rag/langchain_adapters.py
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda


class PortsRetriever(BaseRetriever):
    """Wrap EmbedderPort + VectorStorePort for LangChain."""
    emb: Any
    store: Any
    k: int = 6
    mode: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True  # allow adapter instances

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # defensive: tolerate accidental dict input
        qtext = query["question"] if isinstance(query, dict) else query
        qv = self.emb.embed_query(qtext)

        kwargs = {"k": self.k}
        if self.mode is not None:
            kwargs["mode"] = self.mode
        if self.filters:
            kwargs["filters"] = self.filters
        try:
            hits = self.store.query(qv, **kwargs)
        except TypeError:
            hits = self.store.query(qv, k=self.k)

        docs: List[Document] = []
        for h in hits:
            md = h.get("metadata", {}) if isinstance(h, dict) else {}
            txt = md.get("text") or md.get("chunk") or ""
            docs.append(Document(
                page_content=txt,
                metadata={
                    "doc_id": md.get("doc_id") or md.get("id"),
                    "title": md.get("title"),
                    "name": md.get("name"),
                    "year": md.get("year"),
                    "page": md.get("page"),
                    "url": md.get("url"),
                    "score": h.get("score"),
                },
            ))
        return docs


class RerankDecoratorRetriever(BaseRetriever):
    """Apply your RerankerPort on top of another retriever."""
    base: BaseRetriever
    reranker: Any

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        docs = self.base.get_relevant_documents(query)
        hits = [{
            "score": d.metadata.get("score"),
            "metadata": {"text": d.page_content, **d.metadata}
        } for d in docs]

        try:
            reranked = self.reranker.rerank(query if isinstance(query, str) else query.get("question",""), hits)
        except Exception:
            reranked = hits  # limp along

        out: List[Document] = []
        for h in reranked:
            md = h["metadata"]
            out.append(Document(
                page_content=md.get("text") or "",
                metadata={
                    "doc_id": md.get("doc_id"),
                    "title": md.get("title"),
                    "name": md.get("name"),
                    "year": md.get("year"),
                    "page": md.get("page"),
                    "url": md.get("url"),
                    "score": h.get("score"),
                },
            ))
        return out


def llm_port_runnable(llm) -> Runnable:
    def _call(inputs: Dict[str, Any]) -> Dict[str, Any]:
        answer, usage = llm.chat(
            inputs["system"],
            inputs["user"],
            float(inputs.get("temperature", 0.2)),
            int(inputs.get("max_tokens", 600)),
        )
        return {"answer": answer, "usage": usage}
    return RunnableLambda(_call)
