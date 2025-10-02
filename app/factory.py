"""
app/factory.py

Factory to build the QAPipeline from a YAML runtime config.
- Swaps providers by config (no code edits).
- Supports: OpenAI or Ollama for LLM; Noop or BGE cross-encoder for reranking.
- Validates key files so you don’t learn at runtime that paths are wrong.
"""

from __future__ import annotations
import os
import yaml

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
    # optional, only if you added the file I gave you
    from app.adapters.llm_ollama import OllamaAdapter
except Exception:
    OllamaAdapter = None  # graceful fallback


def _require_file(path: str, label: str) -> None:
    if path and not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")


def build_pipeline(cfg_path: str = "configs/runtime.yaml") -> QAPipeline:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

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

    vs = FaissStoreAdapter(index_path=index_path, ids_path=ids_path, meta_path=meta_path)

    # ---------------- Reranker ----------------
    rr_cfg = cfg.get("reranker", {})
    rr_adapter = rr_cfg.get("adapter", "none").lower()
    if rr_adapter in ("bge_reranker", "bge-reranker"):
        rr_model = rr_cfg.get("model", "BAAI/bge-reranker-base")
        rr = BGERerankerAdapter(model_name=rr_model)
    else:
        rr = NoopReranker()

    # ---------------- LLM ----------------
    llm_cfg = cfg.get("llm", {})
    llm_adapter = llm_cfg.get("adapter", "openai").lower()

    if llm_adapter == "openai":
        model = llm_cfg.get("model", "gpt-4o-mini")
        llm = OpenAIAdapter(model=model)

    elif llm_adapter == "ollama":
        if OllamaAdapter is None:
            raise RuntimeError("llm.adapter=ollama but app.adapters.llm_ollama not available. "
                               "Add the adapter file or switch adapter.")
        model = llm_cfg.get("model", "llama3.1")
        llm = OllamaAdapter(model=model)

    else:
        raise ValueError(f"Unknown llm.adapter: {llm_adapter}")

    return QAPipeline(emb, vs, rr, llm)
