from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import Any

from .base import RawModelItem


class HuggingFaceAdapter:
    """Collect model metadata from the Hugging Face Hub.

    Uses huggingface_hub when installed, with a small HTTP fallback so the
    adapter can still use the public structured API in minimal environments.
    """

    name = "huggingface"

    def __init__(self, limit: int = 50, search_terms: list[str] | None = None) -> None:
        self.limit = limit
        self.search_terms = search_terms or [
            "text-generation",
            "sentence-transformers",
            "embedding",
            "reranker",
        ]

    def fetch_models(self) -> list[RawModelItem]:
        token = os.getenv("HF_TOKEN")
        try:
            # Prefer the official client when it is installed because it handles
            # pagination and model objects for us.
            return self._fetch_with_library(token)
        except Exception:
            # Keep the app usable in lightweight installs that only have the
            # standard library available.
            return self._fetch_with_public_api(token)

    def _fetch_with_library(self, token: str | None) -> list[RawModelItem]:
        from huggingface_hub import HfApi

        api = HfApi(token=token)
        seen: dict[str, RawModelItem] = {}
        per_term_limit = max(10, self.limit // len(self.search_terms))
        for term in self.search_terms:
            # Multiple focused searches catch generation, embedding, and
            # reranking models without pulling the entire Hub.
            models = api.list_models(
                search=term,
                sort="lastModified",
                direction=-1,
                limit=per_term_limit,
                full=True,
            )
            for model in models:
                model_id = getattr(model, "modelId", None) or getattr(model, "id", "")
                if not model_id:
                    continue
                tags = list(getattr(model, "tags", []) or [])
                seen[model_id] = RawModelItem(
                    model_name=model_id,
                    provider=model_id.split("/", 1)[0] if "/" in model_id else "huggingface",
                    source=self.name,
                    source_url=f"https://huggingface.co/{model_id}",
                    tags=tags,
                    raw_metadata={
                        "modelId": model_id,
                        "pipeline_tag": getattr(model, "pipeline_tag", None),
                        "tags": tags,
                        "downloads": getattr(model, "downloads", None),
                        "likes": getattr(model, "likes", None),
                        "lastModified": str(getattr(model, "lastModified", "")),
                        "library_name": getattr(model, "library_name", None),
                    },
                )
                if len(seen) >= self.limit:
                    return list(seen.values())
        return list(seen.values())

    def _fetch_with_public_api(self, token: str | None) -> list[RawModelItem]:
        seen: dict[str, RawModelItem] = {}
        headers = {"User-Agent": "graphrag-llm-dashboard/0.1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for term in self.search_terms:
            params = urllib.parse.urlencode(
                {
                    "search": term,
                    "sort": "lastModified",
                    "direction": "-1",
                    "limit": max(10, self.limit // len(self.search_terms)),
                    "full": "true",
                }
            )
            request = urllib.request.Request(f"https://huggingface.co/api/models?{params}", headers=headers)
            with urllib.request.urlopen(request, timeout=20) as response:
                data: list[dict[str, Any]] = __import__("json").loads(response.read().decode("utf-8"))
            for model in data:
                model_id = model.get("modelId") or model.get("id")
                if not model_id:
                    continue
                tags = list(model.get("tags") or [])
                seen[model_id] = RawModelItem(
                    model_name=model_id,
                    provider=model_id.split("/", 1)[0] if "/" in model_id else "huggingface",
                    source=self.name,
                    source_url=f"https://huggingface.co/{model_id}",
                    tags=tags,
                    raw_metadata=model,
                )
                if len(seen) >= self.limit:
                    return list(seen.values())
        return list(seen.values())
