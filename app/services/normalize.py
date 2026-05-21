from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.adapters.base import RawModelItem
from app.services.classify_graphrag import infer_hardware_fit


def normalize_raw_item(item: RawModelItem) -> dict[str, Any]:
    raw = item.raw_metadata or {}
    model_name = item.model_name
    provider = item.provider or infer_provider(model_name)
    now = datetime.now(timezone.utc).isoformat()

    # Adapters expose different field names; this record is the common shape
    # used by dedupe, classification, database writes, and exports.
    record: dict[str, Any] = {
        "model_name": model_name,
        "provider": provider,
        "source": item.source,
        "source_url": item.source_url,
        "release_date": normalize_release_date(raw.get("release_date") or raw.get("created") or raw.get("created_at")),
        "last_seen_at": now,
        "model_family": raw.get("model_family") or infer_family(model_name),
        "model_type": raw.get("model_type") or infer_model_type(item),
        "parameter_size": raw.get("parameter_size") or infer_parameter_size(model_name),
        "context_window": raw.get("context_window") or infer_context_window(raw),
        "modalities": normalize_modalities(raw.get("modalities") or raw.get("modality") or raw.get("architecture", {}).get("modality")),
        "license": raw.get("license") or raw.get("cardData", {}).get("license"),
        # OpenRouter rows are API-accessible by definition; Ollama and many
        # Hugging Face artifacts are treated as local/open-weight candidates.
        "api_available": bool(raw.get("api_available")) or item.source == "openrouter",
        "local_available": bool(raw.get("local_available")) or item.source == "ollama" or _looks_open_weight(raw, item),
        "hardware_fit": raw.get("hardware_fit"),
        "estimated_cost_input": normalize_cost_per_million(raw.get("estimated_cost_input") or raw.get("pricing", {}).get("prompt")),
        "estimated_cost_output": normalize_cost_per_million(raw.get("estimated_cost_output") or raw.get("pricing", {}).get("completion")),
        "speed_notes": raw.get("speed_notes") or raw.get("speed"),
        "strengths": _as_list(raw.get("strengths")),
        "weaknesses": _as_list(raw.get("weaknesses")),
        "graph_rag_roles": _as_list(raw.get("graph_rag_roles")),
        "graph_rag_score": raw.get("graph_rag_score"),
        "hardware_score": raw.get("hardware_score"),
        "cost_score": raw.get("cost_score"),
        "recommendation": raw.get("recommendation"),
        "notes": raw.get("notes") or "",
        "raw_metadata_json": json.dumps({item.source: raw}, ensure_ascii=False, default=str),
        "tags": list(item.tags or raw.get("tags") or []),
    }
    record["hardware_fit"] = record["hardware_fit"] or infer_hardware_fit(record)
    return record


def normalize_items(items: list[RawModelItem]) -> list[dict[str, Any]]:
    return [normalize_raw_item(item) for item in items]


def infer_provider(model_name: str) -> str:
    # Provider/model IDs are common on hubs like Hugging Face and OpenRouter.
    if "/" in model_name:
        return model_name.split("/", 1)[0]
    lower = model_name.lower()
    known = ["openai", "anthropic", "google", "gemini", "mistral", "meta", "qwen", "deepseek", "gemma", "ollama", "cohere"]
    for provider in known:
        if provider in lower:
            return provider
    return "unknown"


def infer_family(model_name: str) -> str:
    base = model_name.split("/", 1)[-1]
    return re.split(r"[-_: ]", base, maxsplit=1)[0].lower() if base else "unknown"


def infer_model_type(item: RawModelItem) -> str:
    text = " ".join([item.model_name, item.source, " ".join(item.tags), str(item.raw_metadata)]).lower()
    # Classification here is intentionally broad; detailed GraphRAG suitability
    # is scored later in classify_model.
    if is_router_model(item.model_name, item.raw_metadata):
        return "api_router"
    if "embedding" in text or "sentence-transform" in text:
        return "embedding_model"
    if "rerank" in text:
        return "reranker"
    if item.source == "openrouter":
        return "api_only"
    if item.source == "ollama" or item.raw_metadata.get("local_available"):
        return "local_runtime"
    if _looks_open_weight(item.raw_metadata, item):
        return "open_weight"
    return "unknown"


def infer_parameter_size(model_name: str) -> str:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*b(?![a-z])", model_name.lower())
    if match:
        return f"{match.group(1)}B"
    if "moe" in model_name.lower():
        return "MoE"
    return "unknown"


def infer_context_window(raw: dict[str, Any]) -> int | None:
    for key in ("context_length", "context_window", "max_context_length", "max_input_tokens", "max_tokens", "inputTokenLimit"):
        if raw.get(key):
            return _to_int(raw[key])
    top_provider = raw.get("top_provider") or {}
    if top_provider.get("context_length"):
        return _to_int(top_provider["context_length"])
    return None


def normalize_modalities(value: Any) -> list[str]:
    if not value:
        return ["text"]
    if isinstance(value, str):
        lower = value.lower()
        modalities = []
        if "text" in lower:
            modalities.append("text")
        if "image" in lower or "vision" in lower:
            modalities.append("image")
        if "audio" in lower:
            modalities.append("audio")
        if "embedding" in lower:
            modalities.append("embeddings")
        if "multimodal" in lower:
            modalities.append("multimodal")
        return modalities or [lower]
    if isinstance(value, list):
        return [str(item).lower() for item in value]
    return [str(value).lower()]


def normalize_cost_per_million(value: Any) -> float | None:
    """Return USD per 1M tokens."""

    if value in (None, "", "unknown"):
        return None
    try:
        price = float(str(value).replace("$", "").replace(",", ""))
    except ValueError:
        return None
    if price < 0:
        return None
    # Some APIs publish per-token prices, while the dashboard compares cost per
    # million tokens. Tiny positive values are assumed to be per-token.
    if 0 < price < 0.01:
        return price * 1_000_000
    return price


def normalize_release_date(value: Any) -> str | None:
    """Return a readable release date when providers use timestamps."""

    if value in (None, "", "unknown"):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        # Keep ISO-style dates compact and readable in the dashboard.
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return text[:10]
        return text

    # OpenRouter and several API catalogs use Unix seconds; some sources use
    # milliseconds. Only convert plausible modern timestamps.
    if numeric >= 1_000_000_000_000:
        numeric /= 1000
    if numeric >= 1_000_000_000:
        return datetime.fromtimestamp(numeric, timezone.utc).date().isoformat()
    return text


def is_router_model(model_name: str, raw: dict[str, Any] | None = None) -> bool:
    raw = raw or {}
    # Routers are useful catalog entries, but they should not be scored as one
    # fixed model because the real model is selected at request time.
    text = " ".join(
        [
            model_name,
            str(raw.get("name") or ""),
            str(raw.get("description") or ""),
            str((raw.get("architecture") or {}).get("tokenizer") or ""),
        ]
    ).lower()
    return model_name.lower() in {"openrouter/auto"} or "auto router" in text or "meta-model" in text


def _looks_open_weight(raw: dict[str, Any], item: RawModelItem) -> bool:
    text = " ".join([item.source, " ".join(item.tags), str(raw)]).lower()
    return item.source == "huggingface" and any(word in text for word in ["safetensors", "gguf", "transformers", "open"])


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None
