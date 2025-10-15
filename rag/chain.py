# rag/chain.py
"""
LangChain orchestration for the CRDC Knowledge Hub.
Wraps your retriever, optional reranker, and LLM into an LCEL graph.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextvars import ContextVar
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

try:
    from importlib import import_module
except ImportError:  # pragma: no cover - very old Python
    import_module = None

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda, RunnableWithFallbacks

from app.services.qa import QAPipeline

from rag.callbacks import LoggingCallbackHandler
from rag.prompts.structured import (
    SYSTEM_PROMPT,
    StructuredAnswer,
    USER_PROMPT_TEMPLATE,
    ValidationError,
    build_prompt_messages,
    extract_usage,
    format_structured_answer,
    message_to_text,
    prepare_prompt_state,
)
from rag.retrievers import PortsRetriever


def _maybe_load_dotenv() -> None:
    if import_module is None:
        return
    try:
        load_dotenv = import_module("dotenv").load_dotenv  # type: ignore[attr-defined]
    except (ModuleNotFoundError, AttributeError):
        return
    try:
        load_dotenv()
    except Exception:
        pass


_maybe_load_dotenv()
_TIMELINE: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar("_rag_chain_timeline", default=None)


def _init_timeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Reset per-run timing buffer."""
    _TIMELINE.set([])
    return payload


def _record_timing(stage: str, duration: float) -> None:
    """Append a timing entry for the current run."""
    if duration < 0:
        duration = 0.0
    timeline = _TIMELINE.get()
    if timeline is None:
        timeline = []
        _TIMELINE.set(timeline)
    timeline.append({"stage": stage, "seconds": float(duration)})


def _consume_timeline() -> List[Dict[str, Any]]:
    """Return and clear the accumulated timeline."""
    timeline = _TIMELINE.get()
    if timeline is None:
        return []
    snapshot = [
        {"stage": str(entry.get("stage")), "seconds": float(entry.get("seconds", 0.0))}
        for entry in timeline
        if entry
    ]
    _TIMELINE.set(None)
    return snapshot


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


def _structured_chat_runnable(chat_llm):
    def _inner(inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages = inputs.get("messages")
        if not messages:
            raise ValueError("messages missing for structured chat runnable")
        temperature = float(inputs.get("temperature", 0.2))
        max_tokens = int(inputs.get("max_tokens", 600))
        response = chat_llm.invoke(messages, temperature=temperature, max_tokens=max_tokens)
        usage = extract_usage(response)
        raw_text = message_to_text(response)
        try:
            payload = json.loads(raw_text)
            structured = StructuredAnswer(**payload)
        except (json.JSONDecodeError, ValidationError) as exc:  # pragma: no cover - parser guard
            raise ValueError("Structured response parsing failed") from exc
        return {"structured": structured, "usage": usage, "raw": raw_text}

    return RunnableLambda(_inner)


def _chat_plain_runnable(chat_llm):
    def _inner(inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages = inputs.get("messages")
        if not messages:
            raise ValueError("messages missing for chat fallback")
        temperature = float(inputs.get("temperature", 0.2))
        max_tokens = int(inputs.get("max_tokens", 600))
        response = chat_llm.invoke(messages, temperature=temperature, max_tokens=max_tokens)
        usage = extract_usage(response)
        text = message_to_text(response)
        return {"structured": None, "usage": usage, "answer": text, "raw": text}

    return RunnableLambda(_inner)


def _adapter_llm_runnable(llm):
    def _inner(inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs.get("question", "")
        sources_block = inputs.get("sources_block", "")
        temperature = float(inputs.get("temperature", 0.2))
        max_tokens = int(inputs.get("max_tokens", 600))
        user_prompt = USER_PROMPT_TEMPLATE.format(question=question, sources=sources_block)
        answer, usage = llm.chat(SYSTEM_PROMPT, user_prompt, temperature, max_tokens)
        return {"structured": None, "usage": usage, "answer": answer, "raw": answer}

    return RunnableLambda(_inner)


def _native_pipeline_runnable(pipeline: QAPipeline, default_k: int):
    def _inner(inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs.get("question", "")
        temperature = float(inputs.get("temperature", 0.2))
        max_tokens = int(inputs.get("max_tokens", 600))
        k_raw = inputs.get("k", default_k)
        try:
            k_val = int(k_raw) if k_raw is not None else default_k
        except (TypeError, ValueError):
            k_val = default_k
        result = pipeline.ask(question, k=k_val, temperature=temperature, max_tokens=max_tokens)
        answer_text = str(result.get("answer", "") or "")
        if "\nSources:\n" in answer_text:
            answer_main = answer_text.split("\nSources:\n", 1)[0].strip()
        else:
            answer_main = answer_text.strip()
        return {
            "structured": None,
            "usage": result.get("usage"),
            "answer": answer_main,
            "raw": answer_text,
            "citations_override": result.get("sources", []),
        }

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
    candidate_limit: Optional[int] = None,
    candidate_multiplier: int = 8,
    candidate_min: int = 32,
    candidate_overfetch_factor: float = 1.6,
) -> Runnable:
    filters = filters or {}
    langchain_cfg = llm_config or {}
    chat_cfg = {}
    use_chat_openai = False
    if isinstance(langchain_cfg, dict):
        chat_cfg = langchain_cfg.get("chat_openai", {}) or {}
        use_chat_openai = bool(langchain_cfg.get("use_chat_openai"))
    env_use_chat = os.environ.get("LC_USE_CHAT_OPENAI")
    if env_use_chat is not None:
        use_chat_openai = env_use_chat.strip().lower() in {"1", "true", "yes", "on"}

    chat_llm = None
    backup_chat_llm = None
    if use_chat_openai:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "langchain-openai is required for use_chat_openai=true. Install it or disable the flag."
            ) from exc

        model_name = chat_cfg.get("model") or getattr(llm, "model", None) or "gpt-4o-mini"
        temperature_default = chat_cfg.get("temperature")
        if temperature_default is None:
            temperature_default = getattr(llm, "temperature", 0.2)
        max_tokens_default = (
            chat_cfg.get("max_tokens")
            or getattr(llm, "max_tokens", 600)
        )
        max_retries = chat_cfg.get("max_retries")
        timeout = chat_cfg.get("timeout")

        params: Dict[str, Any] = {
            "model": model_name,
            "temperature": float(temperature_default),
            "streaming": bool(langchain_cfg.get("stream", False)),
            "max_tokens": int(max_tokens_default) if max_tokens_default is not None else None,
        }
        if max_retries is not None:
            try:
                params["max_retries"] = int(max_retries)
            except (TypeError, ValueError):
                pass
        if timeout is not None:
            try:
                params["timeout"] = float(timeout)
            except (TypeError, ValueError):
                pass

        params = {k: v for k, v in params.items() if v is not None}
        chat_llm = ChatOpenAI(**params)
        backup_model_name = chat_cfg.get("backup_model") or os.environ.get("LC_CHAT_BACKUP_MODEL")
        if backup_model_name:
            backup_params = dict(params)
            backup_params["model"] = backup_model_name
            backup_chat_llm = ChatOpenAI(**backup_params)

    native_pipeline = QAPipeline(emb, store, reranker, llm)

    if not k:
        k = 6

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

    rerank_topn = None
    if use_rerank and reranker and hasattr(reranker, "topn"):
        try:
            rerank_topn = int(getattr(reranker, "topn"))
        except (TypeError, ValueError):
            rerank_topn = None
    candidate_multiplier = max(1, int(candidate_multiplier)) if candidate_multiplier is not None else 8
    candidate_min = max(1, int(candidate_min)) if candidate_min is not None else 32
    try:
        candidate_overfetch_factor = float(candidate_overfetch_factor)
    except (TypeError, ValueError):
        candidate_overfetch_factor = 1.6
    if candidate_overfetch_factor <= 0:
        candidate_overfetch_factor = 1.6

    computed_candidate = candidate_limit if candidate_limit else max(k * candidate_multiplier, candidate_min)
    if rerank_topn:
        computed_candidate = max(computed_candidate, rerank_topn)
    computed_candidate = max(computed_candidate, k)

    base_retriever_obj = PortsRetriever(
        store=store,
        top_k=computed_candidate,
        neighbors=neighbors,
        contains=contains,
        year_range=year_range,
        diversify_per_doc=diversify_flag,
        candidate_overfetch_factor=candidate_overfetch_factor,
    )
    retriever: Runnable = base_retriever_obj

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

    retrieval_runner: Runnable = _RetrievalRunnable(
        retriever=retriever,
        reranker=reranker if use_rerank and reranker else None,
        base_retriever=base_retriever_obj,
        default_k=k,
        candidate_limit=computed_candidate,
    )

    adapter_runnable = _adapter_llm_runnable(llm)
    pipeline_fallback = _native_pipeline_runnable(native_pipeline, k)

    if chat_llm is not None:
        fallback_runnables: List[Runnable] = []
        if backup_chat_llm is not None:
            fallback_runnables.append(_structured_chat_runnable(backup_chat_llm))
        fallback_runnables.append(_chat_plain_runnable(chat_llm))
        if backup_chat_llm is not None:
            fallback_runnables.append(_chat_plain_runnable(backup_chat_llm))
        fallback_runnables.append(adapter_runnable)
        fallback_runnables.append(pipeline_fallback)
        llm_core = RunnableWithFallbacks(
            runnable=_structured_chat_runnable(chat_llm),
            fallbacks=fallback_runnables,
        )
    else:
        llm_core = RunnableWithFallbacks(
            runnable=adapter_runnable,
            fallbacks=[pipeline_fallback],
        )

    llm_runnable: Runnable = _TimedRunnable("llm", llm_core)

    chain = (
        RunnableLambda(_init_timeline)
        | {
            "question": RunnableLambda(lambda x: x.get("question", "")),
            "docs": retrieval_runner,
            "temperature": RunnableLambda(lambda x: x.get("temperature", 0.2)),
            "max_tokens": RunnableLambda(lambda x: x.get("max_tokens", 600)),
            "k": RunnableLambda(lambda x: x.get("k")),
        }
        | RunnableLambda(prepare_prompt_state)
        | RunnableLambda(lambda state: {**state, "messages": build_prompt_messages(state)})
        | {
            "llm": llm_runnable,
            "citations": RunnableLambda(lambda x: x["citations"]),
        }
        | RunnableLambda(_finalize_output)
    )

    langchain_cfg = langchain_cfg or {}
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


class _TimedRunnable(Runnable):
    """Wrap a runnable to capture its execution duration."""

    def __init__(self, stage: str, inner: Runnable):
        self.stage = stage
        self.inner = inner

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        start = time.perf_counter()
        result = self.inner.invoke(input, config=config, **kwargs)
        _record_timing(self.stage, time.perf_counter() - start)
        return result

    async def ainvoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        start = time.perf_counter()
        try:
            result = await self.inner.ainvoke(input, config=config, **kwargs)
        except (AttributeError, NotImplementedError):
            fn = partial(self.inner.invoke, input, config=config, **kwargs)
            result = await asyncio.to_thread(fn)
        _record_timing(self.stage, time.perf_counter() - start)
        return result


class _RetrievalRunnable(Runnable):
    """Run retrieval (and optional rerank) while recording timings."""

    def __init__(self, retriever: Runnable, reranker: Any | None, *, base_retriever: Any, default_k: int, candidate_limit: int):
        self.retriever = _TimedRunnable("retrieval", retriever)
        self.reranker = reranker
        self._base_retriever = base_retriever
        self._default_k = max(1, int(default_k))
        self._last_summary: Dict[str, float] | None = None
        self._candidate_limit = max(1, int(candidate_limit))

    def _question_text(self, query: Any) -> str:
        if isinstance(query, dict):
            return str(query.get("question", "") or "")
        return str(query or "")

    def _apply_rerank(self, query: Any, docs: List[Document]) -> List[Document]:
        question = self._question_text(query)
        hits = []
        for doc in docs or []:
            md = dict(getattr(doc, "metadata", {}) or {})
            text = getattr(doc, "page_content", "")
            md["text"] = text
            md.setdefault("preview", text)
            base_score = md.get("score")
            faiss_score = md.get("faiss_score", base_score)
            rerank_score = md.get("rerank_score")
            hit_payload = {
                "score": base_score,
                "faiss_score": faiss_score,
                "rerank_score": rerank_score,
                "metadata": md,
            }
            hits.append(hit_payload)

        start = time.perf_counter()
        try:
            reranked = self.reranker.rerank(question, hits)
        except Exception:
            reranked = hits
        if not isinstance(reranked, list):
            reranked = hits
        rerank_elapsed = getattr(self.reranker, "last_run_ms", (time.perf_counter() - start) * 1000.0) / 1000.0
        _record_timing("rerank", rerank_elapsed)

        out_docs: List[Document] = []
        for hit in reranked:
            md = dict(hit.get("metadata", {}) or {})
            text = md.pop("text", "") or md.get("preview", "")
            faiss_score = hit.get("faiss_score", md.get("faiss_score"))
            rerank_score = hit.get("rerank_score")
            if faiss_score is not None:
                md["faiss_score"] = faiss_score
            if rerank_score is not None:
                md["rerank_score"] = rerank_score
                md["score"] = rerank_score
            else:
                md["score"] = hit.get("score")
            out_docs.append(Document(page_content=text, metadata=md))
        return out_docs

    def _should_rerank(self, query: Any) -> bool:
        if self.reranker is None:
            return False
        if isinstance(query, dict) and query.get("rerank") is not None:
            return bool(query["rerank"])
        return True

    def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        docs = self.retriever.invoke(input, config=config, **kwargs)
        timing = getattr(self._base_retriever, "_last_timing", {})
        rerank_ms = 0.0
        rerank_batches = 0
        candidate_count_val = timing.get("candidate_count")
        try:
            candidate_count = int(candidate_count_val)
        except (TypeError, ValueError):
            candidate_count = len(docs) if docs else 0
        candidate_limit_val = timing.get("candidate_limit", self._candidate_limit)
        try:
            candidate_limit = int(candidate_limit_val)
        except (TypeError, ValueError):
            candidate_limit = self._candidate_limit
        overfetch_val = timing.get("overfetch")
        try:
            overfetch = int(overfetch_val)
        except (TypeError, ValueError):
            overfetch = overfetch_val
        print(
            f"[lc.debug] candidates_before_rerank={candidate_count} "
            f"limit={candidate_limit} overfetch={overfetch}"
        )
        if self._should_rerank(input):
            docs = self._apply_rerank(input, docs)
            rerank_ms = getattr(self.reranker, "last_run_ms", 0.0) if self.reranker else 0.0
            rerank_batches = getattr(self.reranker, "last_batches", 0) if self.reranker else 0
            print(
                f"[lc.debug] after_rerank={len(docs)} "
                f"rerank_topn={getattr(self.reranker, 'topn', None)} "
                f"truncate={getattr(self.reranker, 'truncate_chars', None)}"
            )
        docs = docs[: self._default_k]
        print(f"[lc.debug] final_k={len(docs)}")
        ann_ms = timing.get("ann_ms", 0.0)
        stitch_ms = timing.get("stitch_ms", 0.0)
        total_ms = timing.get("total_ms")
        if total_ms is None:
            total_ms = ann_ms + stitch_ms + rerank_ms
        summary = {
            "ann_ms": ann_ms,
            "stitch_ms": stitch_ms,
            "rerank_ms": rerank_ms,
            "total_ms": total_ms,
            "rerank_batches": rerank_batches,
        }
        self._last_summary = summary
        print(
            f"[lc.qa] candidates={candidate_count} limit={candidate_limit} "
            f"ANN={ann_ms:.1f}ms stitch={stitch_ms:.1f}ms rerank={rerank_ms:.1f}ms "
            f"total={total_ms:.1f}ms rerank_batches={rerank_batches}"
        )
        return docs

    async def ainvoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **kwargs) -> List[Document]:
        docs = await self.retriever.ainvoke(input, config=config, **kwargs)
        timing = getattr(self._base_retriever, "_last_timing", {})
        rerank_ms = 0.0
        rerank_batches = 0
        candidate_count_val = timing.get("candidate_count")
        try:
            candidate_count = int(candidate_count_val)
        except (TypeError, ValueError):
            candidate_count = len(docs) if docs else 0
        candidate_limit_val = timing.get("candidate_limit", self._candidate_limit)
        try:
            candidate_limit = int(candidate_limit_val)
        except (TypeError, ValueError):
            candidate_limit = self._candidate_limit
        overfetch_val = timing.get("overfetch")
        try:
            overfetch = int(overfetch_val)
        except (TypeError, ValueError):
            overfetch = overfetch_val
        print(
            f"[lc.debug] candidates_before_rerank={candidate_count} "
            f"limit={candidate_limit} overfetch={overfetch}"
        )
        if self._should_rerank(input):
            docs = self._apply_rerank(input, docs)
            rerank_ms = getattr(self.reranker, "last_run_ms", 0.0) if self.reranker else 0.0
            rerank_batches = getattr(self.reranker, "last_batches", 0) if self.reranker else 0
            print(
                f"[lc.debug] after_rerank={len(docs)} "
                f"rerank_topn={getattr(self.reranker, 'topn', None)} "
                f"truncate={getattr(self.reranker, 'truncate_chars', None)}"
            )
        docs = docs[: self._default_k]
        print(f"[lc.debug] final_k={len(docs)}")
        ann_ms = timing.get("ann_ms", 0.0)
        stitch_ms = timing.get("stitch_ms", 0.0)
        total_ms = timing.get("total_ms")
        if total_ms is None:
            total_ms = ann_ms + stitch_ms + rerank_ms
        summary = {
            "ann_ms": ann_ms,
            "stitch_ms": stitch_ms,
            "rerank_ms": rerank_ms,
            "total_ms": total_ms,
            "rerank_batches": rerank_batches,
        }
        self._last_summary = summary
        print(
            f"[lc.qa] candidates={candidate_count} limit={candidate_limit} "
            f"ANN={ann_ms:.1f}ms stitch={stitch_ms:.1f}ms rerank={rerank_ms:.1f}ms "
            f"total={total_ms:.1f}ms rerank_batches={rerank_batches}"
        )
        return docs


def _finalize_output(out: Dict[str, Any]) -> Dict[str, Any]:
    llm_out = out.get("llm", {}) if isinstance(out, dict) else {}
    citations = llm_out.get("citations_override")
    if not citations:
        citations = out.get("citations", [])
    citations = citations or []

    structured = llm_out.get("structured")
    answer_body = ""
    if isinstance(structured, StructuredAnswer):
        answer_body = format_structured_answer(structured)
        cited_ids = {sid.strip() for sid in structured.cited_sources if isinstance(sid, str)}
        if cited_ids:
            filtered = [c for c in citations if (c.get("sid") or "").strip() in cited_ids]
            if filtered:
                citations = filtered
    else:
        answer_body = str(llm_out.get("answer", "") or "").strip()

    answer_body = answer_body.strip()

    sources_lines: List[str] = []
    for cit in citations:
        sid = cit.get("sid") or ""
        title = cit.get("title") or cit.get("doc_id") or "Source"
        year = cit.get("year")
        page = cit.get("page")
        doc_id = cit.get("doc_id")
        url = cit.get("url")

        bits: List[str] = []
        if year not in (None, ""):
            bits.append(str(year))
        if page not in (None, ""):
            bits.append(f"p.{page}")
        if doc_id:
            bits.append(doc_id)

        suffix = f" ({', '.join(bits)})" if bits else ""
        line = f"{sid} — {title}{suffix}".strip()
        if url:
            line = f"{line} — {url}"
        sources_lines.append(line)

    if sources_lines:
        sources_text = "\n".join(f"- {line}" for line in sources_lines)
        answer_text = answer_body + ("\n\n" if answer_body else "")
        answer_text += f"Sources:\n{sources_text}"
    else:
        answer_text = answer_body or "I could not assemble an answer from the retrieved sources."

    return {
        "answer": answer_text,
        "usage": llm_out.get("usage"),
        "citations": citations,
        "timings": _consume_timeline(),
    }
