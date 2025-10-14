"""
app/factory.py

Factory to build a Q&A pipeline from YAML runtime config.
- Swaps providers by config (no code edits).
- Supports: OpenAI or Ollama for LLM; Noop or BGE cross-encoder for reranking.
- Optional orchestrator toggle: native pipeline vs LangChain chain.
- Validates key files so failures happen at startup, not in a meeting.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from importlib import import_module
except ImportError:  # pragma: no cover - very old Python
    import_module = None


def _maybe_load_dotenv():
    if import_module is None:
        return
    try:
        load_dotenv = import_module("dotenv").load_dotenv  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        return
    except AttributeError:
        return
    try:
        load_dotenv()
    except Exception:
        pass


_maybe_load_dotenv()

# Native pipeline
from app.services.qa import QAPipeline

# Adapter loaders / vector store
from app.adapters.loader import load_embedder
from app.adapters.vector_faiss import FaissStoreAdapter

# Rerankers
from app.adapters.rerank_noop import NoopReranker
from app.adapters.rerank_bge import BGERerankerAdapter  # requires sentence-transformers
from app.adapters.rerank_openai import OpenAIRerankerAdapter

# LLMs
from app.adapters.llm_openai import OpenAIAdapter

try:
    # optional local LLM
    from app.adapters.llm_ollama import OllamaAdapter
except Exception:
    OllamaAdapter = None  # graceful fallback


def _require_file(path: str | Path, label: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")


def _load_cfg(cfg_path: str | Path) -> Dict[str, Any]:
    p = Path(cfg_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Runtime config not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_pipeline(cfg_path: str = None):
    """
    Build and return an object with .ask(question, k, temperature, max_tokens, **kwargs).
    If orchestrator=langchain in config, returns a thin wrapper around a LangChain chain.
    Otherwise returns the native QAPipeline.
    """
    cfg_path = cfg_path or os.environ.get("COTTON_RUNTIME", "configs/runtime.openai.yaml")
    cfg = _load_cfg(cfg_path)

    # ---------------- Embeddings ----------------
    emb = load_embedder(cfg.get("embedder"), os.environ)

    # ---------------- Vector Store ----------------
    vs_cfg = cfg.get("vector_store", {})
    index_path = vs_cfg.get("path", "data/embeddings/vectors.faiss")
    ids_path = vs_cfg.get("ids", "data/embeddings/ids.npy")
    meta_path = vs_cfg.get("meta", "data/staging/chunks.jsonl")

    _require_file(index_path, "FAISS index")
    _require_file(ids_path, "IDs numpy file")
    _require_file(meta_path, "Chunks metadata JSONL")

    store = FaissStoreAdapter(
        index_path=index_path,
        ids_path=ids_path,
        meta_path=meta_path,
        embed_model=cfg.get("embedder", {}).get("model") if isinstance(cfg.get("embedder"), dict) else None,
        embed_config=cfg.get("embedder") if isinstance(cfg.get("embedder"), dict) else None,
    )

    # ---------------- Reranker ----------------
    rr_cfg = cfg.get("reranker", {})
    rr_adapter = (rr_cfg.get("adapter") or "none").lower()
    if rr_adapter in ("bge_reranker", "bge-reranker", "bge"):
        rr_model = rr_cfg.get("model", "BAAI/bge-reranker-base")
        rr_topn = rr_cfg.get("topn")
        rr_batch = rr_cfg.get("batch_size")
        rr_max_len = rr_cfg.get("max_length")
        rr_device = rr_cfg.get("device")
        reranker = BGERerankerAdapter(
            model_name=rr_model,
            topn=int(rr_topn) if rr_topn is not None else 50,
            batch_size=int(rr_batch) if rr_batch is not None else 16,
            max_length=int(rr_max_len) if rr_max_len is not None else 256,
            device=rr_device,
        )
    elif rr_adapter in ("openai", "openai_reranker", "openai-reranker"):
        rr_model = rr_cfg.get("model", "text-embedding-3-large")
        rr_topn = rr_cfg.get("topn")
        rr_max_candidates = rr_cfg.get("max_candidates")
        rr_truncate = rr_cfg.get("truncate_chars", 1200)
        rr_norm = rr_cfg.get("normalize")
        rr_retries = rr_cfg.get("max_retries", 3)
        rr_backoff = rr_cfg.get("retry_backoff", 1.5)
        reranker = OpenAIRerankerAdapter(
            model_name=rr_model,
            topn=int(rr_topn) if rr_topn is not None else 20,
            max_candidates=int(rr_max_candidates) if rr_max_candidates is not None else None,
            truncate_chars=int(rr_truncate),
            normalize=True if rr_norm is None else bool(rr_norm),
            max_retries=int(rr_retries) if rr_retries is not None else 3,
            retry_backoff=float(rr_backoff) if rr_backoff is not None else 1.5,
        )
    else:
        reranker = NoopReranker()

    # ---------------- LLM ----------------
    llm_cfg = cfg.get("llm", {})
    llm_adapter = (llm_cfg.get("adapter") or "openai").lower()

    if llm_adapter == "openai":
        model = llm_cfg.get("model", "gpt-4o-mini")
        llm = OpenAIAdapter(model=model)

    elif llm_adapter == "ollama":
        if OllamaAdapter is None:
            raise RuntimeError(
                "llm.adapter=ollama but app.adapters.llm_ollama not available. "
                "Add the adapter file or switch adapter."
            )
        model = llm_cfg.get("model", "llama3.1")
        llm = OllamaAdapter(model=model)
    else:
        raise ValueError(f"Unknown llm.adapter: {llm_adapter}")

    # ---------------- Orchestrator toggle ----------------
    orchestrator = (cfg.get("orchestrator") or "native").lower()
    if orchestrator == "langchain":
        # Lazy import so native users don't need langchain installed
        try:
            from rag.chain import build_chain  # your LCEL graph
        except Exception as e:
            raise RuntimeError(
                "orchestrator=langchain but rag.chain.build_chain is unavailable. "
                "Install langchain and add rag/langchain_adapters.py + rag/chain.py."
            ) from e

        # Retrieval knobs
        r_cfg = cfg.get("retrieval", {}) or {}
        langchain_cfg = cfg.get("langchain", {}) or {}
        k = int(r_cfg.get("k", 6))
        mode = r_cfg.get("mode", "dense")
        filters = r_cfg.get("filters", {}) or {}
        if "max_preview_chars" not in filters and r_cfg.get("max_preview_chars") is not None:
            filters["max_preview_chars"] = r_cfg.get("max_preview_chars")
        if "max_snippet_chars" not in filters and r_cfg.get("max_snippet_chars") is not None:
            filters["max_snippet_chars"] = r_cfg.get("max_snippet_chars")
        if "neighbors" not in filters and r_cfg.get("neighbors") is not None:
            filters["neighbors"] = r_cfg.get("neighbors")
        if "per_doc" not in filters and r_cfg.get("per_doc") is not None:
            filters["per_doc"] = r_cfg.get("per_doc")
        if "diversify_per_doc" not in filters and r_cfg.get("diversify_per_doc") is not None:
            filters["diversify_per_doc"] = r_cfg.get("diversify_per_doc")
        use_rerank = bool(r_cfg.get("rerank", True))
        use_multiquery = bool(r_cfg.get("use_multiquery", False))
        use_compression = bool(r_cfg.get("use_compression", False))

        chain = build_chain(
            emb=emb,
            store=store,
            reranker=reranker,
            llm=llm,
            k=k,
            mode=mode,
            filters=filters,
            use_rerank=use_rerank,
            use_multiquery=use_multiquery,
            use_compression=use_compression,
            llm_config=langchain_cfg,
        )
        stream_enabled = bool(langchain_cfg.get("stream", False))

        class LangChainWrapper:
            """Expose helpers for sync and streamed answers."""

            def __init__(self, chain, stream_enabled: bool):
                self.chain = chain
                self.stream_enabled = stream_enabled

            @staticmethod
            def _coerce_filters(value: Any) -> Any:
                if value is None:
                    return None
                if hasattr(value, "model_dump"):
                    try:
                        return value.model_dump(exclude_none=True)
                    except Exception:
                        return value.model_dump()
                return value

            def _build_payload(
                self,
                question: str,
                temperature: float,
                max_tokens: int,
                extra: Dict[str, Any],
            ) -> Dict[str, Any]:
                payload: Dict[str, Any] = {
                    "question": question,
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                }
                numeric_keys = {"k", "neighbors", "per_doc", "max_tokens", "max_preview_chars", "max_snippet_chars"}
                for key, raw_value in extra.items():
                    if raw_value is None:
                        continue
                    value = self._coerce_filters(raw_value) if key == "filters" else raw_value
                    if key in numeric_keys:
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            continue
                        if key == "k":
                            value = max(1, value)
                        elif key == "neighbors":
                            value = max(0, value)
                        elif key == "per_doc":
                            value = max(1, value)
                        elif key == "max_tokens":
                            value = max(1, value)
                        elif key == "max_preview_chars":
                            value = max(100, value)
                        elif key == "max_snippet_chars":
                            value = max(100, value)
                    payload[key] = value
                return payload

            def ask(self, question: str, k: int = 6, temperature: float = 0.2, max_tokens: int = 600, **kwargs):
                extras = dict(kwargs)
                extras["k"] = k
                payload = self._build_payload(question, temperature, max_tokens, extras)
                out = self.chain.invoke(payload)
                return {
                    "answer": out.get("answer", ""),
                    "sources": out.get("citations", []),
                    "usage": out.get("usage"),
                    "timings": out.get("timings", []),
                }

            async def stream(self, question: str, temperature: float = 0.2, max_tokens: int = 600, **kwargs):
                if not self.stream_enabled:
                    raise RuntimeError("Streaming not enabled")
                payload = self._build_payload(question, temperature, max_tokens, dict(kwargs))
                root_run_id = None
                async for event in self.chain.astream_events(payload, version="v1"):
                    evt_type = event.get("event")
                    if evt_type == "on_chain_start" and not root_run_id and not event.get("parent_ids"):
                        root_run_id = event.get("run_id")
                    data = event.get("data") or {}
                    if evt_type in {"on_llm_stream", "on_chat_model_stream"}:
                        chunk_payload = data.get("chunk") or data.get("output")
                        chunk_payload = data.get("chunk") or data.get("output")
                        text = None
                        if chunk_payload is None:
                            continue
                        if isinstance(chunk_payload, dict):
                            candidate = chunk_payload.get("content") or chunk_payload.get("text")
                            if isinstance(candidate, list):
                                text = "".join(
                                    item.get("text", "") if isinstance(item, dict) else str(item)
                                    for item in candidate
                                )
                            else:
                                text = candidate if candidate is not None else chunk_payload.get("delta")
                        elif hasattr(chunk_payload, "content"):
                            content = getattr(chunk_payload, "content")
                            if isinstance(content, list):
                                text = "".join(
                                    item.get("text", "") if isinstance(item, dict) else str(item)
                                    for item in content
                                )
                            else:
                                text = content
                        else:
                            text = str(chunk_payload)

                        if text:
                            yield {"type": "token", "token": text}
                    elif evt_type == "on_chain_end" and root_run_id and event.get("run_id") == root_run_id:
                        output = data.get("output") or {}
                        if hasattr(output, "content"):
                            content = getattr(output, "content")
                            if isinstance(content, list):
                                output = {
                                    "answer": "".join(
                                        item.get("text", "") if isinstance(item, dict) else str(item)
                                        for item in content
                                    )
                                }
                            else:
                                output = {"answer": content}
                        yield {"type": "final", "output": output}
                        return

        return LangChainWrapper(chain, stream_enabled)

    # Default: native pipeline
    return QAPipeline(emb, store, reranker, llm)
