# rag/chain.py
"""
LangChain orchestration for the CRDC Knowledge Hub.
Wraps your retriever, optional reranker, and LLM into an LCEL graph.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

from rag.langchain_adapters import PortsRetriever, RerankDecoratorRetriever
from rag.callbacks import LoggingCallbackHandler


SYSTEM_PROMPT = (
    "You are a careful assistant for Australian cotton R&D. "
    "Answer ONLY from the provided source passages. "
    "Include inline citations using [S#] per passage and provide a Sources section."
)


def _sanitize_contains(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [tok.strip() for tok in value.split(",") if tok.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = [str(tok).strip() for tok in value if str(tok).strip()]
    else:
        items = []
    return items or None


def _maybe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prepare_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    question = data["question"]
    docs: List[Document] = data.get("docs", [])
    temperature = float(data.get("temperature", 0.2))
    max_tokens = int(data.get("max_tokens", 600))

    lines: List[str] = []
    citations: List[Dict[str, Any]] = []

    for idx, doc in enumerate(docs, start=1):
        sid = f"S{idx}"
        meta = doc.metadata or {}
        text = doc.page_content or ""
        snippet = text[:500] + ("…" if len(text) > 500 else "")

        title = meta.get("title") or meta.get("doc_id") or "Source"
        doc_id = meta.get("doc_id") or ""
        year = meta.get("year")
        page = meta.get("page")

        parts: List[str] = []
        if doc_id:
            parts.append(doc_id)
        if year not in (None, ""):
            parts.append(str(year))
        if page not in (None, ""):
            parts.append(f"p.{page}")
        suffix = f" ({', '.join(parts)})" if parts else ""

        lines.append(f"[{sid}] {title}{suffix}: {snippet}")

        citations.append(
            {
                "sid": sid,
                "doc_id": doc_id,
                "title": meta.get("title"),
                "year": year,
                "page": page,
                "score": meta.get("score"),
                "chunk_indices": meta.get("chunk_indices"),
                "snippet": text,
            }
        )

    sources_block = "\n".join(lines) if lines else "(no sources)"
    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Source Passages:\n{sources_block}\n\n"
        "Write the answer now. Follow the Rules and include inline [S#] citations."
    )

    return {
        "system": SYSTEM_PROMPT,
        "user": user_prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "citations": citations,
    }


def _call_llm(llm):
    def _inner(inputs: Dict[str, Any]) -> Dict[str, Any]:
        answer, usage = llm.chat(
            inputs.get("system", SYSTEM_PROMPT),
            inputs["user"],
            float(inputs.get("temperature", 0.2)),
            int(inputs.get("max_tokens", 600)),
        )
        return {"answer": answer, "usage": usage}

    return RunnableLambda(_inner)


def build_chain(
    emb: Any,
    store: Any,
    reranker: Any,
    llm: Any,
    k: int = 6,
    mode: str = "dense",
    filters: Dict[str, Any] | None = None,
    use_rerank: bool = True,
    use_multiquery: bool = False,
    use_compression: bool = False,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Runnable:
    filters = filters or {}

    if mode == "router":
        from rag.router_chain import build_router_chain

        return build_router_chain(
            emb=emb,
            store=store,
            reranker=reranker,
            llm=llm,
            default_k=k,
            base_filters=filters,
            use_rerank=use_rerank,
        )

    contains = _sanitize_contains(filters.get("contains"))
    year_min = _maybe_int(filters.get("year_min") or filters.get("year_from"))
    year_max = _maybe_int(filters.get("year_max") or filters.get("year_to"))

    year_range: Optional[Tuple[int, int]]
    if year_min is None and year_max is None:
        year_range = None
    else:
        if year_min is None:
            year_min = year_max
        if year_max is None:
            year_max = year_min
        if year_min is not None and year_max is not None and year_min > year_max:
            year_min, year_max = year_max, year_min
        year_range = (year_min, year_max) if year_min is not None and year_max is not None else None

    neighbors_val = _maybe_int(filters.get("neighbors"))
    neighbors = neighbors_val if neighbors_val is not None and neighbors_val >= 0 else 1

    diversify_flag = filters.get("diversify_per_doc", True)
    if isinstance(diversify_flag, str):
        diversify_flag = diversify_flag.lower() not in {"false", "0", "no"}
    else:
        diversify_flag = bool(diversify_flag)

    retriever: Runnable = PortsRetriever(
        store=store,
        top_k=k,
        neighbors=neighbors,
        contains=contains,
        year_range=year_range,
        diversify_per_doc=diversify_flag,
    )

    if use_multiquery:
        try:
            from langchain.retrievers import MultiQueryRetriever
            adapter_name = (llm_config or {}).get("adapter", "ollama").lower() if isinstance(llm_config, dict) else "ollama"
            model_name = (llm_config or {}).get("model") if isinstance(llm_config, dict) else None

            if adapter_name == "ollama":
                from langchain_community.chat_models import ChatOllama

                retriever_llm = ChatOllama(model=model_name or "llama3.1:8b", temperature=0)
            else:
                from langchain_openai import ChatOpenAI

                retriever_llm = ChatOpenAI(model=model_name or "gpt-4o-mini", temperature=0)

            retriever = MultiQueryRetriever.from_llm(
                retriever=retriever,
                llm=retriever_llm,
            )
        except Exception as exc:
            print(f"[warn] MultiQueryRetriever unavailable: {exc}")

    if use_compression:
        try:
            from langchain.retrievers import ContextualCompressionRetriever
            from langchain.retrievers.document_compressors import EmbeddingsFilter

            class _EmbeddingsWrapper:
                def __init__(self, adapter):
                    self.adapter = adapter

                def embed_documents(self, texts):
                    return self.adapter.embed_texts(list(texts))

                def embed_query(self, text):
                    return self.adapter.embed_query(text)

            embeddings_wrapper = _EmbeddingsWrapper(emb)
            retriever = ContextualCompressionRetriever(
                base_retriever=retriever,
                base_compressor=EmbeddingsFilter(embeddings=embeddings_wrapper),
            )
        except Exception as exc:
            print(f"[warn] Compression retriever unavailable: {exc}")

    if use_rerank and reranker:
        retriever = RerankDecoratorRetriever(base=retriever, reranker=reranker)

    llm_runnable = _call_llm(llm)

    chain = (
        {
            "question": RunnablePassthrough(),
            "docs": retriever,
            "temperature": RunnableLambda(lambda x: x.get("temperature", 0.2)),
            "max_tokens": RunnableLambda(lambda x: x.get("max_tokens", 600)),
        }
        | RunnableLambda(_prepare_payload)
        | {
            "llm": llm_runnable,
            "citations": RunnableLambda(lambda x: x["citations"]),
        }
        | RunnableLambda(lambda out: {
            "answer": out["llm"]["answer"],
            "usage": out["llm"].get("usage"),
            "citations": out["citations"],
        })
    )

    langchain_cfg = llm_config or {}
    callbacks: List[Any] = []
    if langchain_cfg.get("trace"):
        try:
            callbacks.append(LoggingCallbackHandler())
        except Exception as exc:
            print(f"[warn] LoggingCallbackHandler unavailable: {exc}")
    if langchain_cfg.get("stream"):
        callbacks.append(StreamingStdOutCallbackHandler())

    if callbacks:
        chain = chain.with_config(config={"callbacks": callbacks})

    return chain
