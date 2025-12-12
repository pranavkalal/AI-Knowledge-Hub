"""Helpers for dynamically loading embedding adapters based on config/env."""

from __future__ import annotations

import os
from typing import Any, Mapping


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    try:
        return bool(int(value))
    except Exception:
        return default


from app.setting import settings

def load_embedder(embed_cfg: Mapping[str, Any] | None, env: Mapping[str, str] | None = None):
    """Instantiate an embedding adapter based on config/environment."""

    env_map = dict(os.environ if env is None else env)
    cfg = dict(embed_cfg or {})

    adapter_name = cfg.get("adapter") or env_map.get("EMB_ADAPTER") or settings.embedding_adapter or "openai"
    adapter_key = adapter_name.lower()

    normalize = _coerce_bool(cfg.get("normalize"), True)

    batch_size = cfg.get("batch_size", cfg.get("batch", 64))
    try:
        batch_size = int(batch_size)
    except (TypeError, ValueError):
        batch_size = 64

    if adapter_key in {"bge", "bge_local"}:
        model = env_map.get("EMB_MODEL") or cfg.get("model") or "BAAI/bge-small-en-v1.5"
        show_progress = _coerce_bool(cfg.get("show_progress"), True)
        try:
            from app.adapters.embed_bge import BGEEmbeddingAdapter
        except ImportError as exc:  # pragma: no cover - depends on optional deps
            raise ImportError(
                "BGE embedding adapter requires sentence-transformers. Install it or switch adapters."
            ) from exc
        return BGEEmbeddingAdapter(
            model_name=model,
            batch_size=batch_size,
            normalize=normalize,
            show_progress=show_progress,
        )

    if adapter_key in {"openai", "openai_embeddings"}:
        model = env_map.get("EMB_MODEL") or cfg.get("model") or "text-embedding-3-small"
        max_retries = cfg.get("max_retries", 3)
        retry_backoff = cfg.get("retry_backoff", 1.5)
        try:
            max_retries = int(max_retries)
        except (TypeError, ValueError):
            max_retries = 3
        try:
            retry_backoff = float(retry_backoff)
        except (TypeError, ValueError):
            retry_backoff = 1.5
        try:
            from app.adapters.embed_openai import OpenAIEmbeddingAdapter
        except ImportError as exc:  # pragma: no cover - depends on optional deps
            raise ImportError(
                "OpenAI embedding adapter unavailable. Ensure the OpenAI client library is installed."
            ) from exc
        return OpenAIEmbeddingAdapter(
            model_name=model,
            batch_size=batch_size,
            normalize=normalize,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )

    raise ValueError(f"Unknown embedder.adapter: {adapter_name}")

