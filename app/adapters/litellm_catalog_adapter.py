from __future__ import annotations

import json
import urllib.request
from typing import Any

from .base import RawModelItem


class LiteLLMCatalogAdapter:
    """Fetch LiteLLM's public pricing/context catalog from GitHub."""

    name = "litellm_catalog"
    endpoint = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

    def __init__(self, limit: int = 500) -> None:
        self.limit = limit

    def fetch_models(self) -> list[RawModelItem]:
        request = urllib.request.Request(self.endpoint, headers={"User-Agent": "graphrag-llm-dashboard/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))

        items: list[RawModelItem] = []
        for model_name, metadata in payload.items():
            if model_name == "sample_spec" or not isinstance(metadata, dict):
                continue
            provider = str(metadata.get("litellm_provider") or metadata.get("provider") or _provider_from_name(model_name))
            tags = [
                str(value)
                for value in [
                    metadata.get("mode"),
                    "vision" if metadata.get("supports_vision") else "",
                    "function_calling" if metadata.get("supports_function_calling") else "",
                    "audio" if metadata.get("supports_audio_input") else "",
                ]
                if value
            ]
            raw = {
                **metadata,
                "model_name": model_name,
                "api_available": True,
                "local_available": False,
                "model_type": _model_type_from_mode(metadata.get("mode")),
                "context_window": metadata.get("max_input_tokens") or metadata.get("max_tokens"),
                "estimated_cost_input": metadata.get("input_cost_per_token"),
                "estimated_cost_output": metadata.get("output_cost_per_token"),
                "modalities": _modalities(metadata),
            }
            items.append(
                RawModelItem(
                    model_name=f"{provider}/{model_name}" if "/" not in model_name else model_name,
                    provider=provider,
                    source=self.name,
                    source_url="https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json",
                    tags=tags,
                    raw_metadata=raw,
                )
            )
            if len(items) >= self.limit:
                break
        return items


def _provider_from_name(model_name: str) -> str:
    lower = model_name.lower()
    for provider in ("openai", "anthropic", "gemini", "google", "mistral", "cohere", "deepseek", "xai", "groq"):
        if lower.startswith(provider) or f"/{provider}" in lower:
            return "google" if provider == "gemini" else provider
    return "unknown"


def _model_type_from_mode(mode: Any) -> str:
    mode_text = str(mode or "").lower()
    if "embedding" in mode_text:
        return "embedding_model"
    if "rerank" in mode_text:
        return "reranker"
    return "api_only"


def _modalities(metadata: dict[str, Any]) -> list[str]:
    modalities = ["text"]
    if metadata.get("supports_vision"):
        modalities.append("image")
    if metadata.get("supports_audio_input"):
        modalities.append("audio")
    if str(metadata.get("mode") or "").lower() == "embedding":
        modalities.append("embeddings")
    return modalities
