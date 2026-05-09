from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any


EXPORT_FIELDS = [
    "model_name",
    "provider",
    "source",
    "model_type",
    "parameter_size",
    "context_window",
    "modalities",
    "api_available",
    "local_available",
    "hardware_fit",
    "estimated_cost_input",
    "estimated_cost_output",
    "graph_rag_roles",
    "graph_rag_score",
    "hardware_score",
    "cost_score",
    "recommendation",
    "last_seen_at",
]


def export_records_csv(records: list[dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        row = record.copy()
        for field in ("modalities", "graph_rag_roles"):
            if isinstance(row.get(field), list):
                row[field] = "|".join(row[field])
        writer.writerow(row)
    return buffer.getvalue()


def export_records_json(records: list[dict[str, Any]]) -> str:
    return json.dumps(records, indent=2, ensure_ascii=False, default=str)
