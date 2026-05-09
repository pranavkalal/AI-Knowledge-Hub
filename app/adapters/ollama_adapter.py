from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import RawModelItem


class OllamaAdapter:
    """Collect locally installed Ollama model tags when the runtime is present."""

    name = "ollama"

    def __init__(self, endpoint: str = "http://127.0.0.1:11434/api/tags") -> None:
        self.endpoint = endpoint

    def fetch_models(self) -> list[RawModelItem]:
        request = urllib.request.Request(self.endpoint, headers={"User-Agent": "graphrag-llm-dashboard/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, OSError, urllib.error.URLError):
            # Ollama is optional; if it is not running, the rest of the pipeline
            # should continue with remote/manual sources.
            return []

        items: list[RawModelItem] = []
        for model in payload.get("models", []):
            name = model.get("name") or model.get("model")
            if not name:
                continue
            details = model.get("details") or {}
            # Ollama tag details are sparse, so add local-runtime hints here
            # before the shared normalization step.
            family = details.get("family") or str(name).split(":", 1)[0]
            items.append(
                RawModelItem(
                    model_name=str(name),
                    provider="ollama",
                    source=self.name,
                    source_url="http://127.0.0.1:11434/api/tags",
                    tags=[str(family), "local", "ollama"],
                    raw_metadata={
                        **model,
                        "model_family": family,
                        "model_type": "local_runtime",
                        "local_available": True,
                        "api_available": False,
                        "parameter_size": details.get("parameter_size") or "unknown",
                    },
                )
            )
        return items
