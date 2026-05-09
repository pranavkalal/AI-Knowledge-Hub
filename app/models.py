from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ModelRecord(Base):
    __tablename__ = "model_records"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_model_records_dedupe_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(320), index=True)
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    source: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_seen_at: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    model_family: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    parameter_size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    modalities: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(120), nullable=True)
    api_available: Mapped[bool] = mapped_column(Boolean, default=False)
    local_available: Mapped[bool] = mapped_column(Boolean, default=False)
    hardware_fit: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    estimated_cost_input: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_output: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_rag_roles: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_rag_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    hardware_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
