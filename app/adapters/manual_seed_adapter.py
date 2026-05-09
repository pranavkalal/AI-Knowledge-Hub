from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import RawModelItem


class ManualSeedAdapter:
    """Load curated records for sources that are not practical API targets yet."""

    name = "manual_seed"

    def __init__(self, path: str | Path = "data/manual_models.seed.json") -> None:
        self.path = Path(path)

    def fetch_models(self) -> list[RawModelItem]:
        if not self.path.exists():
            return []
        data: list[dict[str, Any]] = json.loads(self.path.read_text(encoding="utf-8"))
        items: list[RawModelItem] = []
        for model in data:
            # Accept either name used by hand-authored seed files.
            name = model.get("model_name") or model.get("name")
            if not name:
                continue
            items.append(
                RawModelItem(
                    model_name=str(name),
                    provider=str(model.get("provider") or "unknown"),
                    source=str(model.get("source") or self.name),
                    source_url=model.get("source_url"),
                    tags=list(model.get("tags") or []),
                    raw_metadata=model,
                )
            )
        return items
