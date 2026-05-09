from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelRecordBase(BaseModel):
    model_name: str
    provider: str
    source: str
    source_url: str | None = None
    release_date: str | None = None
    last_seen_at: str | None = None
    model_family: str | None = None
    model_type: str = "unknown"
    parameter_size: str | None = "unknown"
    context_window: int | None = None
    modalities: list[str] = Field(default_factory=list)
    license: str | None = None
    api_available: bool = False
    local_available: bool = False
    hardware_fit: str = "unknown"
    estimated_cost_input: float | None = None
    estimated_cost_output: float | None = None
    speed_notes: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    graph_rag_roles: list[str] = Field(default_factory=list)
    graph_rag_score: int = 1
    hardware_score: int = 1
    cost_score: int = 1
    recommendation: str = "monitor"
    notes: str | None = None
    classification_notes: list[str] = Field(default_factory=list)
    raw_metadata_json: dict[str, Any] = Field(default_factory=dict)


class ModelRecordRead(ModelRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
