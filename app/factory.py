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
# from app.adapters.rerank_bge import BGERerankerAdapter  # moved to lazy import
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
    cfg_path = cfg_path or os.environ.get("COTTON_RUNTIME", "configs/runtime/openai.yaml")
    cfg = _load_cfg(cfg_path)

    # ---------------- Embeddings ----------------
    emb = load_embedder(cfg.get("embedder"), os.environ)

    # ---------------- Vector Store ----------------
    # ---------------- Vector Store ----------------
    vs_cfg = cfg.get("vector_store", {})
    vs_type = vs_cfg.get("type", "faiss").lower()
    
    if vs_type == "postgres":
        from app.adapters.vector_postgres import PostgresStoreAdapter
        store = PostgresStoreAdapter(
            table_name=vs_cfg.get("table_name", "chunks"),
            connection_string=os.environ.get("POSTGRES_CONNECTION_STRING"),
            embedder=emb
        )
    else:
        # Default to FAISS
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
        from app.adapters.rerank_bge import BGERerankerAdapter
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
                "Install langchain and ensure rag/retrievers/ + rag/chain.py are present."
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
        env_multiquery = os.environ.get("LC_USE_MULTIQUERY")
        if env_multiquery is not None:
            use_multiquery = env_multiquery.strip().lower() in {"1", "true", "yes", "on"}
        env_compression = os.environ.get("LC_USE_COMPRESSION")
        if env_compression is not None:
            use_compression = env_compression.strip().lower() in {"1", "true", "yes", "on"}
        candidate_limit_cfg = r_cfg.get("candidate_limit")
        candidate_multiplier_cfg = r_cfg.get("candidate_multiplier")
        candidate_min_cfg = r_cfg.get("candidate_min") or r_cfg.get("candidate_pool_min")
        candidate_overfetch_factor_cfg = r_cfg.get("candidate_overfetch_factor")

        candidate_limit_override = None
        if candidate_limit_cfg is not None:
            try:
                candidate_limit_override = int(candidate_limit_cfg)
            except (TypeError, ValueError):
                candidate_limit_override = None
        env_candidate_limit = os.environ.get("LC_CANDIDATE_LIMIT")
        if env_candidate_limit is not None:
            try:
                candidate_limit_override = int(env_candidate_limit)
            except (TypeError, ValueError):
                pass

        try:
            candidate_multiplier_val = int(candidate_multiplier_cfg) if candidate_multiplier_cfg is not None else 8
        except (TypeError, ValueError):
            candidate_multiplier_val = 8
        if candidate_multiplier_val <= 0:
            candidate_multiplier_val = 8
        env_candidate_multiplier = os.environ.get("LC_CANDIDATE_MULTIPLIER")
        if env_candidate_multiplier is not None:
            try:
                env_mult = int(env_candidate_multiplier)
            except (TypeError, ValueError):
                env_mult = None
            if env_mult and env_mult > 0:
                candidate_multiplier_val = env_mult

        try:
            candidate_min_val = int(candidate_min_cfg) if candidate_min_cfg is not None else 32
        except (TypeError, ValueError):
            candidate_min_val = 32
        if candidate_min_val <= 0:
            candidate_min_val = k
        env_candidate_min = os.environ.get("LC_CANDIDATE_MIN")
        if env_candidate_min is not None:
            try:
                env_min = int(env_candidate_min)
            except (TypeError, ValueError):
                env_min = None
            if env_min and env_min > 0:
                candidate_min_val = env_min

        try:
            candidate_overfetch_factor_val = float(candidate_overfetch_factor_cfg) if candidate_overfetch_factor_cfg is not None else 1.6
        except (TypeError, ValueError):
            candidate_overfetch_factor_val = 1.6
        if candidate_overfetch_factor_val <= 0:
            candidate_overfetch_factor_val = 1.6
        env_candidate_overfetch = os.environ.get("LC_CANDIDATE_OVERFETCH_FACTOR")
        if env_candidate_overfetch is not None:
            try:
                env_factor = float(env_candidate_overfetch)
            except (TypeError, ValueError):
                env_factor = None
            if env_factor and env_factor > 0:
                candidate_overfetch_factor_val = env_factor

        rerank_topn_val = None
        if hasattr(reranker, "topn"):
            try:
                rerank_topn_val = int(getattr(reranker, "topn"))
            except (TypeError, ValueError):
                rerank_topn_val = None

        if candidate_limit_override is not None and candidate_limit_override <= 0:
            candidate_limit_override = None

        computed_candidate_limit = candidate_limit_override or max(k * candidate_multiplier_val, candidate_min_val)
        if rerank_topn_val:
            computed_candidate_limit = max(computed_candidate_limit, rerank_topn_val)
        computed_candidate_limit = max(computed_candidate_limit, k)

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
            candidate_limit=candidate_limit_override,
            candidate_multiplier=candidate_multiplier_val,
            candidate_min=candidate_min_val,
            candidate_overfetch_factor=candidate_overfetch_factor_val,
        )
        stream_enabled = bool(langchain_cfg.get("stream", False))

        class LangChainWrapper:
            """Expose helpers for sync and streamed answers."""

            def __init__(self, chain, stream_enabled: bool, default_candidate_limit: int, candidate_overfetch_factor: float):
                self.chain = chain
                self.stream_enabled = stream_enabled
                try:
                    self.default_candidate_limit = max(1, int(default_candidate_limit))
                except (TypeError, ValueError):
                    self.default_candidate_limit = max(1, k)
                try:
                    self.default_overfetch_factor = float(candidate_overfetch_factor)
                except (TypeError, ValueError):
                    self.default_overfetch_factor = 1.6
                if self.default_overfetch_factor <= 0:
                    self.default_overfetch_factor = 1.6

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
                payload.setdefault("candidate_limit", self.default_candidate_limit)
                payload.setdefault("candidate_overfetch_factor", self.default_overfetch_factor)
                numeric_keys = {"k", "neighbors", "per_doc", "max_tokens", "max_preview_chars", "max_snippet_chars", "candidate_limit"}
                float_keys = {"candidate_overfetch_factor"}
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
                        elif key == "candidate_limit":
                            value = max(1, value)
                    elif key in float_keys:
                        try:
                            value = float(value)
                        except (TypeError, ValueError):
                            continue
                        if key == "candidate_overfetch_factor" and value <= 0:
                            value = self.default_overfetch_factor
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
                yielded_citations = False
                async for event in self.chain.astream_events(payload, version="v1"):
                    evt_type = event.get("event")
                    if evt_type == "on_chain_start" and not root_run_id and not event.get("parent_ids"):
                        root_run_id = event.get("run_id")
                    
                    data = event.get("data") or {}
                    
                    # Try to capture citations from intermediate steps
                    if not yielded_citations and evt_type == "on_chain_end":
                        output = data.get("output")
                        if isinstance(output, dict) and "citations" in output and isinstance(output["citations"], list):
                            citations = output["citations"]
                            if citations:
                                yield {"type": "sources", "data": citations}
                                yielded_citations = True

                    if evt_type in {"on_llm_stream", "on_chat_model_stream"}:
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
                        # If we haven't yielded citations yet, try to get them from final output
                        if not yielded_citations and isinstance(output, dict) and "citations" in output:
                             yield {"type": "sources", "data": output["citations"]}
                        
                        yield {"type": "final", "output": output}
                        return

        return LangChainWrapper(
            chain,
            stream_enabled,
            default_candidate_limit=computed_candidate_limit,
            candidate_overfetch_factor=candidate_overfetch_factor_val,
        )

    # Default: native pipeline
    return QAPipeline(emb, store, reranker, llm)
