from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class RawModelItem:
    """Raw source payload plus a few normalized hints from an adapter."""

    model_name: str
    provider: str
    source: str
    source_url: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class SourceAdapter(Protocol):
    name: str

    def fetch_models(self) -> list[RawModelItem]:
        """Return source models without mutating storage."""
