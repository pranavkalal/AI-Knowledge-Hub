#!/usr/bin/env python3
"""
Evaluate retrieval quality for both native and LangChain orchestrators.

Usage:
    python scripts/eval_retrieval.py --cfg configs/runtime.yaml \
        --q eval/gold/gold_ai_knowledge_hub.jsonl --k 6
"""

from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from typing import Dict, Iterable, List, Sequence, Tuple

import app.factory as factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval metrics for native vs LangChain pipelines.")
    parser.add_argument("--cfg", default="configs/runtime.yaml", help="Path to runtime YAML config.")
    parser.add_argument(
        "--q",
        default="eval/gold/gold_ai_knowledge_hub.jsonl",
        help="Path to JSONL file with evaluation queries.",
    )
    parser.add_argument("--k", type=int, default=6, help="Top-k depth for metrics.")
    return parser.parse_args()


def load_queries(path: str) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "query" not in obj or "gold_doc_ids" not in obj:
                continue
            gold_ids = obj.get("gold_doc_ids") or []
            obj["gold_doc_ids"] = [str(doc_id) for doc_id in gold_ids if doc_id is not None]
            records.append(obj)
    return records


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def ndcg_at_k(preds: Sequence[str], gold: Iterable[str], k: int) -> float:
    if k <= 0:
        return 0.0
    gold_set = set(gold)
    if not gold_set:
        return 0.0
    dcg = 0.0
    for idx, doc_id in enumerate(preds[:k]):
        if doc_id in gold_set:
            dcg += 1.0 / math.log2(idx + 2)
    ideal_hits = min(len(gold_set), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(preds: Sequence[str], gold: Iterable[str], k: int) -> float:
    gold_set = set(gold)
    if not gold_set or k <= 0:
        return 0.0
    hits = len(gold_set.intersection(preds[:k]))
    return hits / len(gold_set)


def mrr_at_k(preds: Sequence[str], gold: Iterable[str], k: int) -> float:
    gold_set = set(gold)
    if not gold_set or k <= 0:
        return 0.0
    for idx, doc_id in enumerate(preds[:k]):
        if doc_id in gold_set:
            return 1.0 / (idx + 1)
    return 0.0


def _build_pipeline(cfg_path: str, cfg_dict: Dict[str, object]) -> object:
    original_loader = factory._load_cfg  # type: ignore[attr-defined]
    try:
        factory._load_cfg = lambda _: deepcopy(cfg_dict)  # type: ignore[attr-defined]
        return factory.build_pipeline(cfg_path)
    finally:
        factory._load_cfg = original_loader  # type: ignore[attr-defined]


def evaluate_pipeline(
    pipeline: object,
    queries: List[Dict[str, object]],
    *,
    k: int,
    per_doc: int,
    max_tokens: int,
) -> Dict[str, float]:
    ndcg_scores: List[float] = []
    recall_scores: List[float] = []
    mrr_scores: List[float] = []

    for entry in queries:
        question = str(entry.get("query") or "").strip()
        gold_raw = entry.get("gold_doc_ids") if isinstance(entry, dict) else []
        gold_doc_ids: List[str] = gold_raw if isinstance(gold_raw, list) else []
        preds: List[str] = []
        if question:
            try:
                result = pipeline.ask(  # type: ignore[attr-defined]
                    question=question,
                    k=k,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    filters={"per_doc": per_doc},
                )
            except Exception:
                result = {}
            sources = result.get("sources") if isinstance(result, dict) else None
            if isinstance(sources, list):
                for citation in sources[:k]:
                    if isinstance(citation, dict):
                        doc_id = citation.get("doc_id")
                        if doc_id is not None:
                            preds.append(str(doc_id))

        ndcg_scores.append(ndcg_at_k(preds, gold_doc_ids, k))
        recall_scores.append(recall_at_k(preds, gold_doc_ids, k))
        mrr_scores.append(mrr_at_k(preds, gold_doc_ids, k))

    return {
        "queries": len(queries),
        "k": k,
        "per_doc": per_doc,
        "ndcg": _mean(ndcg_scores),
        "recall": _mean(recall_scores),
        "mrr": _mean(mrr_scores),
    }


def main() -> None:
    args = parse_args()
    base_loader = factory._load_cfg  # type: ignore[attr-defined]
    try:
        base_cfg = deepcopy(base_loader(args.cfg))
    except Exception:
        base_cfg = {}

    queries = load_queries(args.q)
    k = max(1, args.k)
    max_tokens = int(base_cfg.get("llm", {}).get("max_output_tokens", 600))  # type: ignore[arg-type]

    orchestrators: List[Tuple[str, str]] = [("native", "native"), ("lc", "langchain")]
    summaries: Dict[str, Dict[str, float]] = {}

    for key, value in orchestrators:
        cfg_variant = deepcopy(base_cfg)
        cfg_variant["orchestrator"] = value  # type: ignore[index]

        retrieval_cfg = cfg_variant.get("retrieval") if isinstance(cfg_variant, dict) else {}
        if not isinstance(retrieval_cfg, dict):
            retrieval_cfg = {}
        filters_cfg = retrieval_cfg.get("filters") if isinstance(retrieval_cfg, dict) else {}
        if not isinstance(filters_cfg, dict):
            filters_cfg = {}
        try:
            per_doc_val = int(filters_cfg.get("per_doc", 2))
        except (TypeError, ValueError):
            per_doc_val = 2
        per_doc = max(1, per_doc_val)
        try:
            pipeline = _build_pipeline(args.cfg, cfg_variant)
        except Exception:
            summaries[key] = {
                "queries": len(queries),
                "k": k,
                "per_doc": per_doc,
                "ndcg": 0.0,
                "recall": 0.0,
                "mrr": 0.0,
            }
            continue

        metrics = evaluate_pipeline(
            pipeline,
            queries,
            k=k,
            per_doc=per_doc,
            max_tokens=max_tokens,
        )
        summaries[key] = metrics

    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == "__main__":
    main()
