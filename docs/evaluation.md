# Evaluation & regression workflows

Keep retrieval quality and latency in check before shipping changes.

## 1. Pytest sanity checks

Focus on the LangChain wrappers:

```bash
python -m pytest tests/langchain
```

- `tests/langchain/test_ports_retriever.py` – ensures chunk stitching, filters, and metadata behave as expected.
- `tests/langchain/test_pipeline_parity.py` – compares native vs LangChain orchestration on a stub corpus.

Add more coverage around ingestion or API layers as needed.

## 2. Retrieval regression harness

Compare before/after metrics using a JSONL query set (`eval/gold/gold_ai_knowledge_hub.jsonl`).

```bash
invoke regress-langchain \
  --before configs/runtime/openai.yaml \
  --after configs/runtime/default.yaml \
  --out reports/regression.json
```

Metrics reported:
- Hit rate, Precision@1, MRR
- Average latency (ms)
- Stage timing deltas (retrieval, rerank, LLM)

Treat a significant drop in recall or spike in latency as a release blocker. Persist `reports/regression.json` in CI artifacts to track trends.

## 3. Ad-hoc CLI queries

Spot check answers using the CLI retriever:

```bash
invoke query -q "How does soil management affect water use efficiency?" --k 8 --neighbors 2
```

Look for correct citations, relevant chunks, and prompt formatting issues.

## 4. Streamlit QA sessions

The UI (`invoke dev`) is ideal for qualitative feedback sessions with domain experts. Encourage them to flag:

- Missing citations or wrong pages
- Incomplete answers (consider multi-query or compression tweaks)
- Latency outliers (HMAC vs cross-encoder rerank toggles)

## 5. Observability hooks

- LangChain callbacks print `[lc.qa]` and `[lc.debug]` lines. Capture them in logs/metrics to watch candidate pools, rerank timings, and final k sizes.
- Extend `_TIMELINE` events in `rag/chain.py` to push custom metrics (Prometheus, Datadog, etc.).

## 6. Performance experiments

When testing new embeddings or rerankers:

1. Run `invoke embed` with new settings (point to a staging embeddings directory).
2. Rebuild FAISS (`invoke faiss --vecs <staging>` if you add a variant command).
3. Run regression harness with a fixed query set.
4. Compare `reports/regression.json` outputs and share diffs with stakeholders.

## 7. Acceptance checklist

- [ ] Pytest suite passing
- [ ] Regression delta within agreed bounds (≤5% hit-rate drop, latency within SLA)
- [ ] Manual spot checks from domain expert
- [ ] No critical warnings in logs (LLM fallbacks, ingestion errors)

Once everything clears, promote the new runtime config or deploy the updated service.
