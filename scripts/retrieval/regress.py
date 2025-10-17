"""
Compare retrieval/QA performance between two runtime configurations.

Measures hit rate, MRR, precision@1, and latency deltas using a fixed query set.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.factory import build_pipeline


def _coerce_path(value: str, base_dir: str | Path = "~") -> Path:
    base = Path(base_dir).expanduser().resolve()
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {path} is outside the allowed directory {base}")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def load_queries(path: Path) -> List[Dict[str, Any]]:
    queries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {idx} of {path}") from exc
            queries.append(payload)
    if not queries:
        raise ValueError(f"No queries found in {path}")
    return queries


@dataclass
class QueryRecord:
    question: str
    expected_doc: str | None
    hit: bool
    rank: int | None
    reciprocal_rank: float
    latency: float
    stages: Dict[str, float]


def _summarise(records: Iterable[QueryRecord]) -> Dict[str, Any]:
    items = list(records)
    total = len(items)
    if total == 0:
        return {
            "count": 0,
            "hit_rate": 0.0,
            "precision_at_1": 0.0,
            "mrr": 0.0,
            "avg_rank": None,
            "avg_latency_ms": 0.0,
            "stages_ms": {},
        }

    hits = sum(1 for rec in items if rec.hit)
    precision_at_1 = sum(1 for rec in items if rec.rank == 1) / total
    mrr = sum(rec.reciprocal_rank for rec in items) / total
    ranks = [rec.rank for rec in items if rec.rank is not None]
    avg_rank = statistics.mean(ranks) if ranks else None
    avg_latency_ms = statistics.mean(rec.latency for rec in items) * 1000.0

    stages: Dict[str, List[float]] = {}
    for rec in items:
        for stage, seconds in rec.stages.items():
            stages.setdefault(stage, []).append(seconds * 1000.0)

    stage_avgs = {
        stage: statistics.mean(values) if values else 0.0
        for stage, values in stages.items()
    }

    return {
        "count": total,
        "hit_rate": hits / total,
        "precision_at_1": precision_at_1,
        "mrr": mrr,
        "avg_rank": avg_rank,
        "avg_latency_ms": avg_latency_ms,
        "stages_ms": stage_avgs,
    }


def evaluate(pipeline, queries: List[Dict[str, Any]], k_override: int | None) -> Tuple[Dict[str, Any], List[QueryRecord]]:
    records: List[QueryRecord] = []
    for item in queries:
        question = item.get("question", "")
        expected_doc = item.get("doc_id")
        k = k_override if k_override is not None else item.get("k")
        kwargs: Dict[str, Any] = {}
        if k is not None:
            try:
                kwargs["k"] = int(k)
            except (TypeError, ValueError):
                pass

        start = time.perf_counter()
        result = pipeline.ask(question=question, **kwargs)
        elapsed = time.perf_counter() - start

        sources = result.get("sources", []) or []
        rank = None
        for idx, source in enumerate(sources, start=1):
            if expected_doc and source.get("doc_id") == expected_doc:
                rank = idx
                break
        hit = rank is not None
        reciprocal = 1.0 / rank if rank else 0.0

        timings = result.get("timings", []) or []
        stage_totals: Dict[str, float] = {}
        for entry in timings:
            stage = entry.get("stage")
            seconds = entry.get("seconds")
            if stage is None or seconds is None:
                continue
            try:
                val = float(seconds)
            except (TypeError, ValueError):
                continue
            stage_totals[stage] = stage_totals.get(stage, 0.0) + val

        records.append(
            QueryRecord(
                question=question,
                expected_doc=expected_doc,
                hit=hit,
                rank=rank,
                reciprocal_rank=reciprocal,
                latency=elapsed,
                stages=stage_totals,
            )
        )
    summary = _summarise(records)
    return summary, records


def compute_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    delta: Dict[str, Any] = {}
    keys = set(before.keys()) | set(after.keys())
    for key in keys:
        if key == "stages_ms":
            before_map = before.get("stages_ms", {}) or {}
            after_map = after.get("stages_ms", {}) or {}
            stage_keys = set(before_map.keys()) | set(after_map.keys())
            delta["stages_ms"] = {
                stage: after_map.get(stage, 0.0) - before_map.get(stage, 0.0)
                for stage in stage_keys
            }
            continue
        before_val = before.get(key)
        after_val = after.get(key)
        if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
            delta[key] = after_val - before_val
    return delta


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare LangChain pipeline metrics before/after changes.")
    parser.add_argument("--before", required=True, help="Runtime config for baseline run.")
    parser.add_argument("--after", required=True, help="Runtime config for updated run.")
    parser.add_argument(
        "--queries",
        default="eval/gold/gold_ai_knowledge_hub.jsonl",
        help="JSONL file with queries and expected doc_ids.",
    )
    parser.add_argument("--k", type=int, default=None, help="Override top-k for all queries.")
    parser.add_argument("--out", type=str, default=None, help="Optional path to write JSON results.")
    args = parser.parse_args()

    before_cfg = _coerce_path(args.before)
    after_cfg = _coerce_path(args.after)
    queries_path = _coerce_path(args.queries)
    queries = load_queries(queries_path)

    print(f"[regress] loading baseline pipeline from {before_cfg}")
    baseline = build_pipeline(str(before_cfg))
    before_summary, before_records = evaluate(baseline, queries, args.k)

    print(f"[regress] loading candidate pipeline from {after_cfg}")
    candidate = build_pipeline(str(after_cfg))
    after_summary, after_records = evaluate(candidate, queries, args.k)

    delta = compute_delta(before_summary, after_summary)

    report = {
        "before": before_summary,
        "after": after_summary,
        "delta": delta,
        "queries": len(queries),
    }

    print(json.dumps(report, indent=2, sort_keys=True))

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "before": before_summary,
                    "after": after_summary,
                    "delta": delta,
                    "before_records": [rec.__dict__ for rec in before_records],
                    "after_records": [rec.__dict__ for rec in after_records],
                },
                fh,
                indent=2,
                sort_keys=True,
            )
        print(f"[regress] wrote detailed report to {out_path}")


if __name__ == "__main__":
    main()
