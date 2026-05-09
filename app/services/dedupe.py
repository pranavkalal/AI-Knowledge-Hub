from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge likely duplicate model records across sources."""

    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        key = dedupe_key(record)
        if key not in merged:
            merged[key] = record.copy()
            merged[key]["source"] = record.get("source") or "unknown"
            continue
        merged[key] = merge_records(merged[key], record)
    return list(merged.values())


def dedupe_key(record: dict[str, Any]) -> str:
    provider = normalize_provider(record.get("provider") or "")
    name = normalize_name(record.get("model_name") or "")
    # Include provider when known so unrelated models with the same short name
    # do not collapse into one row.
    if provider and provider != "unknown":
        return f"{provider}:{name}"
    return name


def merge_records(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = existing.copy()
    # Numeric scores/capabilities should keep the strongest observed value,
    # while descriptive fields keep the first useful value already collected.
    prefer_max = {"context_window", "graph_rag_score", "hardware_score", "cost_score"}
    prefer_truthy = {
        "api_available",
        "local_available",
        "source_url",
        "release_date",
        "model_family",
        "model_type",
        "parameter_size",
        "license",
        "hardware_fit",
        "estimated_cost_input",
        "estimated_cost_output",
        "speed_notes",
        "recommendation",
        "notes",
    }
    list_fields = {"modalities", "strengths", "weaknesses", "graph_rag_roles", "tags"}

    for field in prefer_max:
        merged[field] = _max_value(merged.get(field), incoming.get(field))
    for field in prefer_truthy:
        merged[field] = merged.get(field) or incoming.get(field)
    for field in list_fields:
        merged[field] = _merge_lists(merged.get(field), incoming.get(field))

    # Keep every source name visible so users can see where a merged row came
    # from without opening the raw metadata.
    merged["source"] = ", ".join(_merge_lists(merged.get("source", "").split(", "), [incoming.get("source")]))
    merged["last_seen_at"] = _latest_datetime(merged.get("last_seen_at"), incoming.get("last_seen_at"))
    merged["raw_metadata_json"] = merge_raw_metadata(merged.get("raw_metadata_json"), incoming.get("raw_metadata_json"))
    return merged


def merge_raw_metadata(left: Any, right: Any) -> str:
    left_obj = _json_obj(left)
    right_obj = _json_obj(right)
    merged = left_obj.copy()
    for key, value in right_obj.items():
        # Preserve conflicting payloads instead of choosing one source's raw
        # data and losing the other.
        if key in merged and merged[key] != value:
            existing = merged[key] if isinstance(merged[key], list) else [merged[key]]
            existing.append(value)
            merged[key] = existing
        else:
            merged[key] = value
    return json.dumps(merged, ensure_ascii=False, default=str)


def normalize_name(value: str) -> str:
    name = value.lower().strip()
    # Remove hub owner prefixes so "meta/llama-x" and "llama-x" can meet after
    # provider normalization.
    if "/" in name:
        name = name.split("/", 1)[1]
    name = re.sub(r"[^a-z0-9.]+", "-", name)
    return name.strip("-")


def normalize_provider(value: str) -> str:
    provider = value.lower().strip()
    aliases = {
        "meta-llama": "meta",
        "facebook": "meta",
        "google-deepmind": "google",
        "qwenlm": "qwen",
        "thebloke": "unknown",
    }
    return aliases.get(provider, provider)


def _merge_lists(left: Any, right: Any) -> list[str]:
    result: list[str] = []
    for value in _as_list(left) + _as_list(right):
        clean = str(value).strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _max_value(left: Any, right: Any) -> Any:
    left_num = _to_float(left)
    right_num = _to_float(right)
    if left_num is None:
        return right
    if right_num is None:
        return left
    return left if left_num >= right_num else right


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, "", "unknown"):
            return None
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _latest_datetime(left: Any, right: Any) -> Any:
    left_dt = _parse_datetime(left)
    right_dt = _parse_datetime(right)
    if left_dt and right_dt:
        return left if left_dt >= right_dt else right
    return left or right


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _json_obj(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"value": value}
