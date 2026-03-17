# GraphRAG Research Review

## Executive Summary

GraphRAG is not one pattern but a family of graph-aware retrieval approaches. The right design depends on the questions the system must answer.

Standard vector RAG is often enough for local passage retrieval, but it becomes weaker when the system must handle:

- cross-document entity linking
- filtering, counting, sorting, and aggregation
- multi-hop reasoning across entities and relationships
- explainability and provenance
- corpus-level summarization and thematic questions

For this project, the strongest strategic direction is:

- use Neo4j as the primary graph-plus-vector substrate when one system must support graph structure, chunks, embeddings, and traversals together
- avoid treating Microsoft GraphRAG as the default unless the main workload is corpus-level summarization over large unstructured text collections
- prefer a custom Neo4j-centered GraphRAG architecture for enterprise retrieval that needs precision, hybrid search, text2cypher, and explainability
- borrow Microsoft GraphRAG ideas selectively, especially local versus global retrieval modes and summary layers where they add measurable value

## 1. Why Vanilla RAG Is Not Enough

Chunk-only retrieval is useful, but it has consistent weaknesses:

- it retrieves semantically similar passages but often misses exact relationships
- it struggles with aggregation and filtering tasks
- it struggles with entity disambiguation
- it can lose document boundaries and source coherence
- it is weak on dataset-wide or thematic questions

In practice, vector-only RAG is usually not enough for questions such as:

- Which contracts expiring in the next 90 days mention a specific clause?
- Which incidents involve the same customer, product, and region?
- What major themes appear across a large research corpus?

The first two require structured reasoning. The third benefits from higher-level graph summarization.

## 2. What Knowledge Graphs Add

Knowledge graphs improve RAG by combining structured facts with unstructured context.

### Entity grounding

Entity mentions in text can be linked to canonical nodes, improving retrieval consistency and reducing duplication.

### Multi-hop retrieval

Graphs make it natural to move from one entity to related entities, events, documents, and claims.

### Precise filtering and aggregation

Graphs support counts, constraints, joins, and path-aware filtering much better than embeddings alone.

### Explainability

Graph traversals and linked evidence are easier to inspect than pure vector matches.

### Hybrid retrieval

The strongest systems combine:

- vector similarity
- keyword or full-text retrieval
- graph traversal
- structured query generation
- reranking or routing where needed

## 3. Core GraphRAG Patterns

### Hybrid retrieval

The practical entry point is usually vector retrieval plus keyword or full-text search. This improves recall by covering different failure modes.

### Advanced retrieval patterns

Parent-document retrieval and similar strategies improve recall by retrieving on smaller units while returning richer surrounding context.

### Text2Cypher

Text2cypher is one of the most important enterprise GraphRAG patterns because it turns natural-language questions into precise graph queries.

It works best when the prompt includes:

- schema information
- terminology mappings
- few-shot examples
- output constraints

The main risk is prompt fragility if the schema is unclear or drifts over time.

### Agentic GraphRAG

An agentic pattern routes between multiple retrievers, such as:

- vector retrieval for unstructured context
- graph traversal for neighborhood discovery
- text2cypher for structured questions
- fallback tools for simpler cases

This pattern is useful when one retriever is not enough for the question mix.

### Graph construction from unstructured text

Many teams do not start with a graph. They start with PDFs, reports, tickets, and transcripts. LLMs can help extract entities, relationships, and structured fields from those sources, but graph construction still requires schema design, entity resolution, and quality control.

### Microsoft-style GraphRAG

Microsoft GraphRAG is best understood as a hierarchical summarization architecture. It extracts entities and relationships, detects communities, summarizes those communities, and uses specialized query modes to answer both local and global questions.

## 4. Microsoft GraphRAG

### What it is

Microsoft GraphRAG builds a graph from raw text, creates community hierarchies, generates community summaries, and uses those artifacts at query time.

The main query modes commonly discussed are:

- Global Search for corpus-level questions
- Local Search for entity-centric questions
- DRIFT-style or related graph-aware search modes for entity-focused retrieval with wider context
- Basic Search for more standard retrieval cases

### Strengths

- strong fit for global or thematic questions
- useful for large narrative or report-style corpora
- clear separation between local and global retrieval behavior
- valuable as a source of reusable design patterns

### Weaknesses

- heavier indexing pipeline than simpler graph-aware systems
- prompt sensitivity and tuning requirements
- higher operational complexity
- can be overkill for precise, structured enterprise QA

### Bottom line

Microsoft GraphRAG is most compelling when the hardest questions are broad, corpus-wide, and summarization-heavy. It is less compelling as a default for entity-centric enterprise retrieval.

### LazyGraphRAG

Microsoft's LazyGraphRAG direction is important because it shows movement toward lower-cost, more adaptive graph-aware retrieval rather than treating the original heavy indexing pipeline as the only path.

## 5. Neo4j Evaluation

### Why Neo4j is a strong candidate

Neo4j is compelling because it combines:

- graph-native modeling and traversal
- Cypher query support
- vector indexes
- full-text search
- graph and vector retrieval in one operational surface

The core advantage is co-location of symbolic and semantic retrieval.

### Where Neo4j is especially strong

Neo4j is a strong fit when:

- the data has explicit entities and relationships
- the system needs multi-hop reasoning
- explainability matters
- the same system should hold chunks, embeddings, entities, and traversals
- the workload mixes semantic and structured questions

### Cautions

Neo4j is less compelling when:

- the workload is only vector search with little graph logic
- the team cannot invest in schema design and entity resolution
- text2cypher quality will not be monitored carefully

### Verdict

Neo4j is recommended as the primary database when the target system is genuinely graph-aware rather than only vector-aware.

## 6. Strategy Comparison

The decision should not be framed as Microsoft GraphRAG versus Neo4j because they address different layers of the stack.

- Microsoft GraphRAG is a retrieval and summarization architecture
- Neo4j is a graph and retrieval substrate
- a custom implementation can use Neo4j while borrowing Microsoft GraphRAG ideas selectively

### Comparison table

| Criterion | Microsoft GraphRAG | Custom Neo4j-Centered GraphRAG |
| --- | --- | --- |
| Best fit | corpus-level summarization and thematic discovery | enterprise QA, entity-centric retrieval, filtering, aggregation |
| Core mechanism | community detection, summaries, specialized query modes | hybrid retrieval, graph traversal, text2cypher, routing |
| Indexing cost | higher | variable, often lower |
| Explainability | good | very strong with explicit traversals and queries |
| Global thematic questions | strong | can be added selectively |
| Structured exact queries | indirect | strong |
| Operational flexibility | medium | high |

### Recommended middle-ground strategy

For many teams, the best path is:

1. adopt Neo4j as the main graph-plus-vector substrate
2. start with hybrid retrieval, graph traversal, and text2cypher
3. add agentic routing only where the question mix requires it
4. add summary layers or local/global retrieval modes only if evaluation shows a real need

## 7. Relevant Alternatives

Recent alternatives matter because they show the architecture space is moving toward more adaptive and lower-cost graph-aware retrieval.

### LightRAG

Useful as a lighter graph-aware retrieval design reference.

### KG2RAG

Relevant for graph-guided expansion of semantically retrieved chunks.

### FRAG

Useful as a model of modular, query-adaptive knowledge-graph RAG.

### LazyGraphRAG

Important as a Microsoft-backed signal that lower-cost graph-aware retrieval is strategically valuable.

## 8. Evaluation Guidance

GraphRAG systems should be evaluated on at least three axes:

1. Did the system retrieve the needed evidence?
2. Did the answer remain grounded in that evidence?
3. Was the answer correct and complete?

The core metrics reflected in the source material are:

- context recall
- faithfulness
- answer correctness

### Recommended benchmark buckets

- local factual questions
- structured or aggregation questions
- multi-hop relational questions
- global summarization questions

This benchmark design makes it easier to decide whether summary-heavy GraphRAG patterns are actually useful for the target workload.

## 9. Recommended Direction

The strongest recommendation is to adopt a custom Neo4j-centered GraphRAG as the primary direction and incorporate Microsoft GraphRAG ideas selectively rather than wholesale.

### Why this direction is strongest

- it covers the broadest enterprise retrieval needs
- it supports both semantic and structured retrieval
- it preserves explainability and provenance
- it avoids paying the full cost of summary-heavy indexing unless the workload proves it is needed
- it keeps the architecture flexible as the system matures

### Suggested phased roadmap

#### Phase 1 - minimum viable GraphRAG

- Neo4j as graph-plus-vector store
- chunk embeddings and full-text indexes
- hybrid retrieval
- basic graph schema and provenance
- benchmark covering local, structured, multi-hop, and global questions

#### Phase 2 - retrieval maturity

- text2cypher
- graph traversal-based context expansion
- entity resolution workflow
- reranking and metadata-aware filtering

#### Phase 3 - selective summary layers

- entity summaries
- community detection
- local versus global retrieval modes
- thematic answer generation if evaluation justifies it

### Key risks and mitigations

- graph extraction quality can be noisy -> start with curated high-value entities and relations
- text2cypher can be brittle -> use schema prompts, terminology mappings, and few-shot examples
- summary-heavy GraphRAG can be overengineered -> add it only when benchmarks show a real gap
- architecture debates can outrun evidence -> formalize benchmarks early

## References

- Essential GraphRAG: Knowledge Graph-Enhanced RAG, Tomaž Bratanič and Oskar Hane, Manning, 2025
- Microsoft GraphRAG documentation and related Microsoft Research publications on GraphRAG, LazyGraphRAG, and BenchmarkQED
- Neo4j documentation on vector indexes, GenAI support, and GraphRAG-related tooling
- Recent research on LightRAG, KG2RAG, and FRAG
