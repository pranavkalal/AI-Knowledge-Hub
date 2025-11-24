#!/usr/bin/env python3
"""
Evaluate generation quality using RAGAS metrics.

Usage:
    python scripts/evaluation/eval_generation.py --cfg configs/runtime/openai.yaml \\
        --q eval/gold/gold_ai_knowledge_hub.jsonl --k 6
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

# Load env vars for API keys
from dotenv import load_dotenv
load_dotenv()

import app.factory as factory
from datasets import Dataset
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    faithfulness,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate generation quality with RAGAS metrics.")
    parser.add_argument("--cfg", default="configs/runtime/openai.yaml", help="Path to runtime YAML config.")
    parser.add_argument(
        "--q",
        default="eval/gold/gold_ai_knowledge_hub.jsonl",
        help="Path to JSONL file with evaluation queries and gold answers.",
    )
    parser.add_argument("--k", type=int, default=6, help="Top-k for retrieval.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of queries to test.")
    return parser.parse_args()


def load_queries(path: str) -> List[Dict[str, Any]]:
    """Load evaluation queries with gold answers."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "query" not in obj or "gold_answer" not in obj:
                continue
            obj.setdefault("gold_doc_ids", [])
            records.append(obj)
    return records


def run_pipeline(pipeline: Any, question: str, k: int) -> Dict[str, Any]:
    """Run RAG pipeline and extract answer + contexts."""
    try:
        result = pipeline.ask(
            question=question,
            k=k,
            temperature=0.2,
            max_tokens=600,
        )
    except Exception as e:
        print(f"[error] Pipeline failed for question: {question[:50]}... Error: {e}")
        return {"answer": "", "contexts": [], "sources": []}

    answer = result.get("answer", "")
    sources = result.get("sources", [])
    
    # Extract contexts (the text snippets from retrieved documents)
    contexts = []
    for source in sources[:k]:
        if isinstance(source, dict):
            # Try to get the text/preview from the source
            text = source.get("text") or source.get("preview") or ""
            if text:
                contexts.append(text)
    
    return {
        "answer": answer,
        "contexts": contexts,
        "sources": sources,
    }


def main() -> None:
    args = parse_args()
    
    # Build pipeline
    pipeline = factory.build_pipeline(args.cfg)
    
    # Load queries
    queries = load_queries(args.q)
    if args.limit:
        queries = queries[:args.limit]
    
    print(f"[eval] Evaluating {len(queries)} queries with RAGAS...")
    
    # Prepare RAGAS dataset
    questions_list: List[str] = []
    ground_truths_list: List[str] = []
    answers_list: List[str] = []
    contexts_list: List[List[str]] = []
    
    for entry in queries:
        question = entry["query"]
        gold_answer = entry["gold_answer"]
        
        # Run pipeline
        result = run_pipeline(pipeline, question, args.k)
        
        # Collect data for RAGAS
        questions_list.append(question)
        ground_truths_list.append(gold_answer)
        answers_list.append(result["answer"])
        contexts_list.append(result["contexts"])
    
    # Create RAGAS dataset
    ragas_data = {
        "question": questions_list,
        "answer": answers_list,
        "contexts": contexts_list,
        "ground_truth": ground_truths_list,
    }
    
    dataset = Dataset.from_dict(ragas_data)
    
    # Evaluate
    print("[eval] Running RAGAS evaluation...")
    metrics = [
        faithfulness,        # Answer is grounded in contexts (no hallucinations)
        answer_relevancy,    # Answer addresses the question
        context_precision,   # Retrieved contexts are relevant
    ]
    
    # Configure RAGAS to use OpenAI via LangChain wrapper
    eval_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o", temperature=0))
    
    results = evaluate(dataset, metrics=metrics, llm=eval_llm)
    
    # Extract mean scores (RAGAS returns EvaluationResult object)
    def get_mean_score(metric_name: str) -> float:
        """Extract mean score from RAGAS result."""
        try:
            value = results[metric_name]
        except (KeyError, TypeError):
            return 0.0
        
        if value is None:
            return 0.0
        # Handle DataFrame/Series
        if hasattr(value, 'mean'):
            return float(value.mean())
        # Handle list
        if isinstance(value, list):
            return float(sum(value) / len(value)) if value else 0.0
        # Handle scalar
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    faithfulness_score = get_mean_score("faithfulness")
    relevancy_score = get_mean_score("answer_relevancy")
    precision_score = get_mean_score("context_precision")
    
    # Print results
    print("\n" + "="*60)
    print("RAGAS Evaluation Results")
    print("="*60)
    print(f"Queries evaluated: {len(queries)}")
    print(f"Retrieval k: {args.k}")
    print()
    print(f"Faithfulness:       {faithfulness_score:.3f}")
    print(f"Answer Relevancy:   {relevancy_score:.3f}")
    print(f"Context Precision:  {precision_score:.3f}")
    print("="*60)
    
    # Write results to JSON
    output_path = Path("eval/results/generation_metrics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "n_queries": len(queries),
            "k": args.k,
            "faithfulness": faithfulness_score,
            "answer_relevancy": relevancy_score,
            "context_precision": precision_score,
        }, f, indent=2)
    
    print(f"\n✅ Results saved to {output_path}")


if __name__ == "__main__":
    main()
