# app/service/search_service.py
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.adapters.vector_faiss import FaissStoreAdapter
from app.services.formatting import format_citation, format_snippet
from rag.retrieval.utils import resolve_retrieval_settings, prepare_hits

DEFAULTS = dict(k=8, neighbors=2, per_doc=2, max_preview_chars=1800, max_snippet_chars=180)
ROOT = Path(__file__).resolve().parents[2]   # project root


@lru_cache(maxsize=1)
def _load_store() -> FaissStoreAdapter:
    index_path = os.environ.get("FAISS_INDEX_PATH", "data/embeddings/vectors.faiss")
    ids_path = os.environ.get("FAISS_IDS_PATH", "data/embeddings/ids.npy")
    meta_path = os.environ.get("FAISS_META_PATH", "data/staging/chunks.jsonl")

    for label, path in (("FAISS index", index_path), ("FAISS ids", ids_path), ("chunks metadata", meta_path)):
        if not Path(path).exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    return FaissStoreAdapter(index_path=index_path, ids_path=ids_path, meta_path=meta_path)


def search(
    query: str,
    top_k: int = DEFAULTS["k"],
    neighbors: int = DEFAULTS["neighbors"],
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Query the FAISS store directly and return formatted search results."""
    store = _load_store()

    settings_filters: Dict[str, Any] = dict(filters or {})
    settings_filters.setdefault("neighbors", neighbors)
    settings_filters.setdefault("per_doc", DEFAULTS["per_doc"])
    settings_filters.setdefault("max_preview_chars", DEFAULTS["max_preview_chars"])
    settings_filters.setdefault("max_snippet_chars", DEFAULTS["max_snippet_chars"])

    settings = resolve_retrieval_settings(settings_filters)

    overfetch = max(top_k * 5, 50)
    raw_hits = store.search_raw(query, top_k=overfetch)
    hits = prepare_hits(raw_hits, store, settings, limit=top_k)

    results: List[Dict[str, Any]] = []
    snippet_len = settings.max_snippet_chars if hasattr(settings, "max_snippet_chars") else DEFAULTS["max_snippet_chars"]

    for hit in hits:
        meta = hit.get("metadata", {}) if isinstance(hit, dict) else {}
        chunk_id = meta.get("id") or hit.get("id") or ""
        doc_id = meta.get("doc_id") or chunk_id.split("_chunk")[0]

        citation = format_citation(hit)
        preview = format_snippet(meta.get("preview") or meta.get("text") or "", length=snippet_len)

        chunk_index = meta.get("chunk_index")
        if chunk_index is None and "_chunk" in chunk_id:
            try:
                chunk_index = int(chunk_id.split("_chunk")[-1])
            except ValueError:
                chunk_index = 0

        results.append({
            "doc_id": doc_id,
            "chunk_id": int(chunk_index or 0),
            "score": citation.get("score", 0.0),
            "title": citation.get("title"),
            "year": citation.get("year"),
            "preview": preview,
            "page": citation.get("page"),
            "pdf_url": citation.get("url") or meta.get("url"),
            "source_url": citation.get("source_url") or meta.get("source_url"),
            "rel_path": citation.get("rel_path") or meta.get("rel_path"),
            "filename": meta.get("filename"),
        })

    return results


def search_service(
    q: str,
    k: int | None = None,
    neighbors: int | None = None,
    per_doc: int | None = None,
    contains: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> Dict[str, Any]:
    k = k or DEFAULTS["k"]
    neighbors = neighbors if neighbors is not None else DEFAULTS["neighbors"]
    per_doc = per_doc if per_doc is not None else DEFAULTS["per_doc"]

    filters: Dict[str, Any] = {
        "contains": contains,
        "year_min": year_min,
        "year_max": year_max,
        "neighbors": neighbors,
        "per_doc": per_doc,
        "max_preview_chars": DEFAULTS["max_preview_chars"],
        "max_snippet_chars": DEFAULTS["max_snippet_chars"],
    }

    results = search(q, top_k=k, neighbors=neighbors, filters=filters)

    return {
        "query": q,
        "params": {
            "k": k,
            "neighbors": neighbors,
            "per_doc": per_doc,
            "contains": contains,
            "year_min": year_min,
            "year_max": year_max,
        },
        "count": len(results),
        "results": results,
    }
