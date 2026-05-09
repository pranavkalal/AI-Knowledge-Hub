from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import RawModelItem


class MistralAdapter:
    """Fetch available Mistral models when MISTRAL_API_KEY is configured."""

    name = "mistral"
    endpoint = "https://api.mistral.ai/v1/models"

    def fetch_models(self) -> list[RawModelItem]:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            return []
        request = urllib.request.Request(
            self.endpoint,
            headers={"Authorization": f"Bearer {api_key}", "User-Agent": "graphrag-llm-dashboard/0.1"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload: dict[str, Any] | list[dict[str, Any]] = json.loads(response.read().decode("utf-8"))

        models = payload.get("data", []) if isinstance(payload, dict) else payload
        items: list[RawModelItem] = []
        for model in models:
            model_id = model.get("id") or model.get("root")
            if not model_id:
                continue
            capabilities = model.get("capabilities") or {}
            raw = {
                **model,
                "api_available": True,
                "local_available": False,
                "model_type": "api_only",
                "context_window": model.get("max_context_length"),
                "modalities": ["text", "image"] if capabilities.get("vision") else ["text"],
            }
            tags = ["coding"] if capabilities.get("completion_fim") else []
            if capabilities.get("function_calling"):
                tags.append("tool-use")
            if capabilities.get("vision"):
                tags.append("vision")
            items.append(
                RawModelItem(
                    model_name=f"mistral/{model_id}",
                    provider="mistral",
                    source=self.name,
                    source_url="https://docs.mistral.ai/getting-started/models/",
                    tags=tags,
                    raw_metadata=raw,
                )
            )
        return items
