"""
Factory to build the QAPipeline from a YAML runtime config.
Keeps provider choices out of the code; swapping is a config change.
"""

import yaml
from app.services.qa import QAPipeline

# Adapters
from app.adapters.embed_bge import BGEEmbeddingAdapter
from app.adapters.rerank_bge import BGERerankerAdapter
from app.adapters.vector_faiss import FaissStoreAdapter
from app.adapters.rerank_noop import NoopReranker
from app.adapters.llm_openai import OpenAIAdapter

def build_pipeline(cfg_path: str = "configs/runtime.yaml") -> QAPipeline:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    emb_cfg = cfg["embedder"]
    vs_cfg = cfg["vector_store"]
    rr_cfg = cfg["reranker"]
    llm_cfg = cfg["llm"]

    # Embedder
    emb = BGEEmbeddingAdapter(emb_cfg.get("model", "BAAI/bge-small-en-v1.5"))

    # Vector store
    vs = FaissStoreAdapter(
        index_path=vs_cfg["path"],
        ids_path=vs_cfg["ids"],
        meta_path=vs_cfg.get("meta", "data/staging/chunks.jsonl"),
    )

    # Reranker (no-op for now)
    rr = NoopReranker()

    # LLM
    llm = OpenAIAdapter(model=llm_cfg.get("model", "gpt-4o-mini"))

    return QAPipeline(emb, vs, rr, llm)
