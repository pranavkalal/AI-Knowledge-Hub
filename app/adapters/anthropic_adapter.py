from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import RawModelItem


class AnthropicAdapter:
    """Fetch available Anthropic API models when ANTHROPIC_API_KEY is configured."""

    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/models"

    def fetch_models(self) -> list[RawModelItem]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return []
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "graphrag-llm-dashboard/0.1",
        }
        request = urllib.request.Request(self.endpoint, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))

        items: list[RawModelItem] = []
        for model in payload.get("data", []):
            model_id = model.get("id")
            if not model_id:
                continue
            raw = {
                **model,
                "api_available": True,
                "local_available": False,
                "model_type": "api_only",
                "modalities": ["text", "image"],
            }
            items.append(
                RawModelItem(
                    model_name=f"anthropic/{model_id}",
                    provider="anthropic",
                    source=self.name,
                    source_url="https://docs.anthropic.com/en/docs/about-claude/models",
                    tags=["reasoning", "coding", "vision"],
                    raw_metadata=raw,
                )
            )
        return items
