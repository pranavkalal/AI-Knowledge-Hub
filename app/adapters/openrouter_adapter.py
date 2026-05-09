from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import RawModelItem


class OpenRouterAdapter:
    """Collect API-accessible models from OpenRouter's models endpoint."""

    name = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/models"

    def fetch_models(self) -> list[RawModelItem]:
        headers = {"User-Agent": "graphrag-llm-dashboard/0.1"}
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            # OpenRouter's public endpoint works without a key, but a key may
            # unlock fuller or more reliable metadata depending on account setup.
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(self.endpoint, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))

        items: list[RawModelItem] = []
        for model in payload.get("data", []):
            model_id = model.get("id") or model.get("name")
            if not model_id:
                continue
            # OpenRouter IDs commonly look like provider/model-name.
            provider = str(model_id).split("/", 1)[0] if "/" in str(model_id) else "openrouter"
            items.append(
                RawModelItem(
                    model_name=str(model_id),
                    provider=provider,
                    source=self.name,
                    source_url=f"https://openrouter.ai/{model_id}",
                    tags=self._tags_from_model(model),
                    raw_metadata=model,
                )
            )
        return items

    @staticmethod
    def _tags_from_model(model: dict[str, Any]) -> list[str]:
        tags = []
        architecture = model.get("architecture") or {}
        modality = architecture.get("modality")
        tokenizer = architecture.get("tokenizer")
        instruct_type = architecture.get("instruct_type")
        for value in (modality, tokenizer, instruct_type):
            if value:
                tags.append(str(value))
        if model.get("top_provider", {}).get("is_moderated"):
            tags.append("moderated")
        return tags
