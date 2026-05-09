from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from .base import RawModelItem


class GeminiAdapter:
    """Fetch Google Gemini models when GEMINI_API_KEY is configured."""

    name = "google_gemini"
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models"

    def fetch_models(self) -> list[RawModelItem]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return []

        items: list[RawModelItem] = []
        page_token = ""
        while True:
            query = {"key": api_key, "pageSize": "1000"}
            if page_token:
                query["pageToken"] = page_token
            request = urllib.request.Request(
                f"{self.endpoint}?{urllib.parse.urlencode(query)}",
                headers={"User-Agent": "graphrag-llm-dashboard/0.1"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            for model in payload.get("models", []):
                name = str(model.get("name") or "").replace("models/", "")
                if not name:
                    continue
                methods = model.get("supportedGenerationMethods") or []
                raw = {
                    **model,
                    "api_available": True,
                    "local_available": False,
                    "model_type": "embedding_model" if any("embed" in str(method).lower() for method in methods) else "api_only",
                    "context_window": model.get("inputTokenLimit"),
                    "modalities": _modalities(model),
                }
                items.append(
                    RawModelItem(
                        model_name=f"google/{name}",
                        provider="google",
                        source=self.name,
                        source_url="https://ai.google.dev/gemini-api/docs/models",
                        tags=_tags(model),
                        raw_metadata=raw,
                    )
                )
            page_token = payload.get("nextPageToken") or ""
            if not page_token:
                return items


def _modalities(model: dict[str, Any]) -> list[str]:
    text = " ".join(str(model.get(key) or "") for key in ("name", "displayName", "description")).lower()
    modalities = ["text"]
    if any(token in text for token in ("vision", "image", "multimodal")):
        modalities.append("image")
    if "audio" in text:
        modalities.append("audio")
    if "embed" in text:
        modalities.append("embeddings")
    return modalities


def _tags(model: dict[str, Any]) -> list[str]:
    text = " ".join(str(model.get(key) or "") for key in ("name", "displayName", "description")).lower()
    tags = []
    for token in ("reasoning", "thinking", "vision", "audio", "embedding", "code", "coding"):
        if token in text:
            tags.append(token)
    return tags
