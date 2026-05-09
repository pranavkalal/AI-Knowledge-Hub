from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.base import SourceAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.huggingface_adapter import HuggingFaceAdapter
from app.adapters.litellm_catalog_adapter import LiteLLMCatalogAdapter
from app.adapters.manual_seed_adapter import ManualSeedAdapter
from app.adapters.mistral_adapter import MistralAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.openrouter_adapter import OpenRouterAdapter
from app.models import ModelRecord
from app.services.classify_graphrag import classify_model
from app.services.dedupe import dedupe_key, dedupe_records, merge_records
from app.services.normalize import normalize_items


JSON_LIST_FIELDS = {"modalities", "strengths", "weaknesses", "graph_rag_roles", "classification_notes", "tags"}


@dataclass(slots=True)
class PipelineResult:
    fetched: int
    normalized: int
    upserted: int
    errors: list[str]


def default_adapters(include_network: bool = True) -> list[SourceAdapter]:
    # Ollama is local and quick to check; the remaining adapters may need
    # network access or API metadata, so tests can disable them.
    adapters: list[SourceAdapter] = [OllamaAdapter()]
    if include_network:
        adapters.extend(
            [
                OpenRouterAdapter(),
                HuggingFaceAdapter(limit=40),
                LiteLLMCatalogAdapter(limit=500),
                OpenAIAdapter(),
                AnthropicAdapter(),
                GeminiAdapter(),
                MistralAdapter(),
            ]
        )
    return adapters


def run_update_pipeline(db: Session, adapters: Iterable[SourceAdapter] | None = None) -> PipelineResult:
    adapters = list(adapters or default_adapters(include_network=True))
    raw_items = []
    errors: list[str] = []
    # Treat each source independently so one failed provider does not block the
    # whole refresh.
    for adapter in adapters:
        try:
            raw_items.extend(adapter.fetch_models())
        except Exception as exc:
            errors.append(f"{getattr(adapter, 'name', adapter.__class__.__name__)} failed: {exc}")

    # Source payloads are normalized first, merged across providers second, then
    # classified so scores are based on the richest combined record.
    normalized = [classify_model(record) for record in dedupe_records(normalize_items(raw_items))]
    upserted = upsert_records(db, normalized)
    return PipelineResult(fetched=len(raw_items), normalized=len(normalized), upserted=upserted, errors=errors)


def import_manual_seed(db: Session, path: str = "data/manual_models.seed.json") -> PipelineResult:
    adapter = ManualSeedAdapter(path)
    return run_update_pipeline(db, adapters=[adapter])


def reclassify_all(db: Session) -> int:
    records = db.query(ModelRecord).all()
    for model in records:
        # Re-score from stored data without refetching external catalogs.
        data = db_model_to_dict(model)
        classified = classify_model(data)
        apply_record_data(model, classified)
    db.commit()
    return len(records)


def upsert_records(db: Session, records: list[dict]) -> int:
    count = 0
    for record in records:
        key = dedupe_key(record)
        record["dedupe_key"] = key
        existing = db.query(ModelRecord).filter(ModelRecord.dedupe_key == key).one_or_none()
        if existing:
            # Merge instead of replacing so older useful metadata is preserved
            # when a newer source has only partial fields.
            merged = merge_records(db_model_to_dict(existing), record)
            merged["dedupe_key"] = key
            apply_record_data(existing, merged)
        else:
            existing = ModelRecord(dedupe_key=key, model_name=record["model_name"], provider=record["provider"], source=record["source"])
            apply_record_data(existing, record)
            db.add(existing)
        count += 1
    db.commit()
    return count


def db_model_to_dict(model: ModelRecord) -> dict:
    data = {}
    for column in ModelRecord.__table__.columns:
        value = getattr(model, column.name)
        # Convert JSON-backed columns back to Python values before merging,
        # classifying, or exporting.
        if column.name in JSON_LIST_FIELDS:
            value = _json_loads(value, [])
        elif column.name == "raw_metadata_json":
            value = value or "{}"
        data[column.name] = value
    return data


def apply_record_data(model: ModelRecord, record: dict) -> None:
    for key, value in record.items():
        if not hasattr(model, key):
            continue
        # Keep storage types stable even when adapters send strings, numbers, or
        # already-parsed JSON values.
        if key in JSON_LIST_FIELDS:
            value = json.dumps(value or [], ensure_ascii=False)
        elif key == "raw_metadata_json" and isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False, default=str)
        elif key in {"estimated_cost_input", "estimated_cost_output"}:
            value = _to_float(value)
        elif key in {"context_window", "graph_rag_score", "hardware_score", "cost_score"}:
            value = _to_int(value)
        setattr(model, key, value)


def records_for_export(db: Session) -> list[dict]:
    return [db_model_to_dict(record) for record in db.query(ModelRecord).all()]


def _json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _to_float(value):
    if value in (None, "", "unknown"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    if value in (None, "", "unknown"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
