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
    from dotenv import load_dotenv  # optional, but nice for local dev
    load_dotenv()
except Exception:
    pass

# Native pipeline
from app.services.qa import QAPipeline

# Adapters (embedding + vector)
from app.adapters.embed_bge import BGEEmbeddingAdapter
from app.adapters.vector_faiss import FaissStoreAdapter

# Rerankers
from app.adapters.rerank_noop import NoopReranker
from app.adapters.rerank_bge import BGERerankerAdapter  # requires sentence-transformers

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
    cfg_path = cfg_path or os.environ.get("COTTON_RUNTIME", "configs/runtime.yaml")
    cfg = _load_cfg(cfg_path)

    # ---------------- Embeddings ----------------
    emb_cfg = cfg.get("embedder", {})
    emb_model = emb_cfg.get("model", "BAAI/bge-small-en-v1.5")
    emb = BGEEmbeddingAdapter(emb_model)

    # ---------------- Vector Store ----------------
    vs_cfg = cfg.get("vector_store", {})
    index_path = vs_cfg.get("path", "data/embeddings/vectors.faiss")
    ids_path   = vs_cfg.get("ids",  "data/embeddings/ids.npy")
    meta_path  = vs_cfg.get("meta", "data/staging/chunks.jsonl")

    _require_file(index_path, "FAISS index")
    _require_file(ids_path,   "IDs numpy file")
    _require_file(meta_path,  "Chunks metadata JSONL")

    store = FaissStoreAdapter(index_path=index_path, ids_path=ids_path, meta_path=meta_path)

    # ---------------- Reranker ----------------
    rr_cfg = cfg.get("reranker", {})
    rr_adapter = (rr_cfg.get("adapter") or "none").lower()
    if rr_adapter in ("bge_reranker", "bge-reranker", "bge"):
        rr_model = rr_cfg.get("model", "BAAI/bge-reranker-base")
        reranker = BGERerankerAdapter(model_name=rr_model)
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

            def ask(self, question: str, k: int = 6, temperature: float = 0.2, max_tokens: int = 600, **kwargs):
                payload = {
                    "question": question,
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                }
                out = self.chain.invoke(payload)
                return {
                    "answer": out.get("answer", ""),
                    "sources": out.get("citations", []),
                    "usage": out.get("usage"),
                }

            async def stream(self, question: str, temperature: float = 0.2, max_tokens: int = 600, **kwargs):
                if not self.stream_enabled:
                    raise RuntimeError("Streaming not enabled")
                payload = {
                    "question": question,
                    "temperature": float(temperature),
                    "max_tokens": int(max_tokens),
                }
                async for event in self.chain.astream_events(payload):
                    evt_type = event.get("event")
                    data = event.get("data") or {}
                    if evt_type == "on_llm_stream":
                        chunk = data.get("chunk")
                        if isinstance(chunk, dict):
                            chunk = chunk.get("content") or chunk.get("text")
                        if chunk:
                            yield {"type": "token", "token": chunk}
                    elif evt_type == "on_chain_end":
                        output = data.get("output") or {}
                        yield {"type": "final", "output": output}
                        return

        return LangChainWrapper(chain, stream_enabled)

    # Default: native pipeline
    return QAPipeline(emb, store, reranker, llm)
