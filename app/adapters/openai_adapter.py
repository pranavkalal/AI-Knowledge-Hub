from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import RawModelItem


class OpenAIAdapter:
    """Fetch available OpenAI API models when OPENAI_API_KEY is configured."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/models"

    def fetch_models(self) -> list[RawModelItem]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return []
        request = urllib.request.Request(
            self.endpoint,
            headers={"Authorization": f"Bearer {api_key}", "User-Agent": "graphrag-llm-dashboard/0.1"},
        )
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
                "modalities": _modalities(str(model_id)),
            }
            items.append(
                RawModelItem(
                    model_name=f"openai/{model_id}",
                    provider="openai",
                    source=self.name,
                    source_url="https://platform.openai.com/docs/models",
                    tags=_tags(str(model_id)),
                    raw_metadata=raw,
                )
            )
        return items


def _modalities(model_id: str) -> list[str]:
    modalities = ["text"]
    if any(token in model_id.lower() for token in ("vision", "gpt-4o", "gpt-4.1", "omni")):
        modalities.append("image")
    if "embedding" in model_id.lower():
        modalities.append("embeddings")
    return modalities


def _tags(model_id: str) -> list[str]:
    tags = []
    lower = model_id.lower()
    if "embedding" in lower:
        tags.append("embedding")
    if any(token in lower for token in ("gpt-4", "gpt-5", "o1", "o3", "o4")):
        tags.extend(["reasoning", "coding"])
    return tags
