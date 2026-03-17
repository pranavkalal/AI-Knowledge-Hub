# Evaluation Strategy: Comparing Strategies and Models

## Overview

This outlines the proposed framework used to evaluate and compare different system configurations within the project.

Rather than evaluating a single architecture, this framework, this enables a systematic comparison of multiple strategies, such as:

- retrieval methods
- orchestration strategies
- model choices

The goal is to provide a repeatable and consistent method for testiung how changes to the system affect performance.

---

# Why?

The system is designed as a modular pipeline, where individual components can be modified independently.

Evaluation focuses on:

- isolating variables
- testing one change at a time
- measuring impact across multiple metrics

This ensures that results are interpretable and actionable

---

# Configurable Components

The following are valid components to be varied:

## Retrieval Strategy

- Hybrid RAG
- GraphRAG
- Community based retrieval

## Orchestration Strategy

- Static Pipeline
- Agentic workflow

## Embedding Model

- Different embedding models
- different chunking strategies

## Reranking

- With cross-encoder
- Without reranker
- Different rerankers

## Generation Models

- Different LLMs
- Different prompt strategies

---

# Experiment Degsign

## Controlled Experiments

Each experiment modifies one variable at a time while keeping all others constant, i.e.:

|Experiment|Variable Changed|
|---|---|
|E1|Embedding Model|
|E2|Retrieval Strategy|
|E3|Reranker enabled/disabled|
|E4|Orchestration Strategy|

## A/B Testing

Experiments are conducted using A/B testing:

- COnfig A: Baseline
- Config B: Modified

Both configurations are tested on the same query set.

---

# Query Set

A standardised query set is used for all experiments.

## Query Categories

- Factual queries
    - Simple lookups with direct answers
    - Example: "What yield imporvement was observed in cultivar X?"
- Relational queries
    - Requires understanding relationships between entities
    - Example: "How does irrigation impact cotton yield?”
- Multi-hop queries
    - Requires combining information across documents
    - Example: “Which trials link drought resistance to specific cultivars?”
- Thematic/Analytical queries
    - Requires high-level reasoning across the corpus
    - Example: “What are the major research themes in CRDC reports?”

This ensures evaluation across all system use cases.

---

# Evaluation Metrics

## 1. Answer Quality

Evaluated using a scoring rubric:

- Correctness
- Completeness
- Relevance
- Groundedness

## 2. Retrieval Quality

- Precision@k
- Recall@k
- Relevance of retrieved context

## 3. Efficiency Metrics

- Response latency
- Token usage
- Computational cost

---

# Experiment Workflow

1. Select variable to test
2. Define baseline configuration
3. Define modified configuration
4. Run both configurations on query set
5. Record outputs and metrics
6. Compare results

---

# Result Recording

Each experiment should record:
- Configuratiuon details
- Query(s)
- Retrieved context
- Generated Answer
- Eval Scores

Results to be stored in both CSV and markdown summaries

---

# Analysis

Results should be analysed across
- Average score per query type
- Strengths and weaknesses
- Failure cases
- Trade-offs

---

# Documenting Results

All experiment results should be documented in markdown - in 'docs/evals/results'.
Each experiment should include:
- Objective
- Configs
- Results
- Analysis
- COnclusion

---

# Summary

This frameworks allows:
- consistent comparison of system configs
- controlled experimentation
- evidence based design decisions

It will support ongoing optimisation of the system as new models and strategies are introduced.