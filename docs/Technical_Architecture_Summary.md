# CRDC Knowledge Hub — Technical Architecture Summary

**Domain**: Agricultural Research Knowledge Retrieval | **Type**: Retrieval-Augmented Generation (RAG) System

---

## 1. System Architecture

The CRDC Knowledge Hub implements a **production-grade RAG pipeline** for semantic retrieval over ~3,000 agricultural research PDFs. The architecture employs a multi-stage retrieval strategy combining approximate nearest neighbor (ANN) search with cross-encoder reranking.

### Storage Migration: SQLite → PostgreSQL with pgvector

The initial prototype utilized SQLite with FAISS for vector similarity search. This approach proved untenable at scale due to:

1. **Index persistence limitations** — FAISS indices required manual serialization and lacked transactional guarantees
2. **Hybrid search complexity** — Combining vector and keyword search required custom orchestration across disparate systems
3. **Operational overhead** — No native support for concurrent writes during ingestion workloads

The production system migrates to **PostgreSQL with pgvector**, enabling:

- **HNSW indexing** (`vector_cosine_ops`) for sub-linear ANN search on 3072-dimensional embeddings
- **Native hybrid retrieval** via CTEs combining `embedding <=> query` (cosine distance) with `ts_rank_cd` (BM25-style keyword scoring) in a single query: `0.8 × vector_score + 0.2 × keyword_score`
- **JSONB metadata filtering** with computed indexes for temporal queries (e.g., `metadata->>'year'`)
- **ACID compliance** for concurrent ingestion and retrieval workloads

---

## 2. Data Ingestion Strategy

### Parser Migration: Docling → Azure Document Intelligence

The legacy pipeline used **Docling** (IBM's open-source parser), which exhibited degraded accuracy on:

- Multi-column layouts common in research publications
- Embedded tables with complex cell structures
- Figures with inline captions

The current implementation uses **Azure Document Intelligence** (`prebuilt-layout` model with `markdown` output format), which provides:

1. **Structured markdown extraction** — Preserves heading hierarchy, tables as markdown syntax, and list formatting
2. **Line-level bounding boxes** — Polygon coordinates (`[x1,y1,x2,y2,...]`) enable precise UI deep-linking to source text
3. **Page-aware spans** — Content offsets mapped per page for accurate chunk-to-page association

### Chunking Pipeline

```
PDF → Azure DI (markdown + bboxes) → Semantic Chunker → Bbox Mapper → OpenAI Embed → PostgreSQL
```

- **Semantic chunking**: `RecursiveCharacterTextSplitter` with 600 tokens/chunk, 100 token overlap
- **Bbox mapping**: Fuzzy matching algorithm maps chunk text to source line polygons for UI highlighting
- **Embedding model**: `text-embedding-3-large` (3072 dimensions) via OpenAI API

---

## 3. LLM Integration

### Context Retrieval & Generation Flow

```
Query → Embed → Hybrid Search (pgvector) → Rerank (top-k) → Prompt Assembly → GPT-4o → Streaming Response
```

1. **Retrieval**: Query embedding compared against chunk vectors via hybrid search; candidates overfetched by 2× for reranking
2. **Reranking**: Cross-encoder scoring using cosine similarity between query and candidate embeddings (`text-embedding-3-large`)
3. **Prompt construction**: Retrieved chunks formatted as `[S{i}] {title} (p.{page})\n{text}` with persona-specific system prompts
4. **Generation**: `gpt-4o` with structured output parsing; streaming via LangChain Expression Language (LCEL)
5. **Citation grounding**: LLM outputs reference cited source IDs, filtered against retrieved chunks for verifiability

### Orchestration

The pipeline is implemented as an **LCEL graph** (`rag/chain.py`) with:

- Timed runnable wrappers for latency instrumentation
- Fallback chains (structured → plain → adapter → native pipeline)
- Persona-aware prompt injection supporting `grower`, `researcher`, and `extension` modes

---

## 4. Stack & Technologies

| Layer | Technology | Specification |
|-------|------------|---------------|
| **Document Parsing** | Azure Document Intelligence | `prebuilt-layout`, markdown output, line polygons |
| **Vector Database** | PostgreSQL + pgvector | HNSW index, 3072-dim vectors, hybrid search |
| **Embeddings** | OpenAI `text-embedding-3-large` | 3072 dimensions |
| **LLM** | OpenAI `gpt-4o` | Streaming generation, 0.2 temperature |
| **Reranker** | OpenAI embeddings | Cross-encoder similarity scoring |
| **Backend** | FastAPI | Async endpoints, SSE streaming |
| **Orchestration** | LangChain (LCEL) | Runnable composition, callbacks |
| **Frontend** | Next.js + React | PDF viewer with bbox highlighting |
| **Infrastructure** | Docker Compose | PostgreSQL service containerization |

---

## 5. Engineering Decisions Summary

| Decision | Rationale |
|----------|-----------|
| pgvector over FAISS | Unified storage, hybrid search, ACID compliance |
| Azure DI over Docling | Superior table/layout parsing, bounding box fidelity |
| Semantic chunking | Respects document structure, reduces mid-sentence splits |
| Two-stage retrieval | ANN for recall, reranking for precision |
| LCEL orchestration | Composable, observable, streaming-native |

---

*Document generated for Research Fellow application — December 2024*
