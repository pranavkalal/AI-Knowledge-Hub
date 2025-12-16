# AI Knowledge Hub - Architecture

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Parsing** | Azure Document Intelligence | Extract Markdown + bounding boxes from PDFs |
| **Storage** | PostgreSQL + pgvector | Vector store with hybrid search |
| **Embeddings** | OpenAI `text-embedding-3-large` | 3072-dim vectors for retrieval |
| **LLM** | OpenAI `gpt-4o` | Answer generation |
| **Reranker** | OpenAI `text-embedding-3-large` | Cross-encoder reranking |
| **Orchestration** | LangGraph | Agentic RAG pipeline with Corrective RAG pattern |
| **Backend** | FastAPI + LangChain | API and adapter layer |
| **Frontend** | Next.js + React + Tailwind | Chat UI with PDF viewer |

---

## Pipeline Overview

The system uses **LangGraph** to implement a **Corrective RAG** pattern with self-healing query rewriting and hallucination detection.

```mermaid
flowchart TB
    subgraph Ingestion
        PDF[PDF Files] --> Azure[Azure DI]
        Azure --> Chunk[Semantic Chunker]
        Chunk --> Embed[OpenAI Embed]
        Embed --> PG[(PostgreSQL)]
    end
    
    subgraph "LangGraph RAG Pipeline"
        Query[User Query] --> Retrieve[Retrieve]
        Retrieve --> Grade[Grade Relevance]
        Grade -->|Poor Results| Rewrite[Rewrite Query]
        Rewrite -->|Max 2 retries| Retrieve
        Grade -->|Good Results| Rerank[Rerank]
        Rerank --> Generate[Generate Answer]
        Generate --> Evaluate[Self-Evaluate]
        Evaluate --> Answer[Streaming Response]
    end
    PG --> Retrieve
```

---

## Directory Structure

```
AI-Knowledge-Hub/
├── app/                      # FastAPI Backend
│   ├── main.py              # App entrypoint
│   ├── factory.py           # Pipeline builder from config
│   ├── ingest.py            # Ingestion CLI
│   ├── routers/             # API endpoints
│   │   ├── ask.py           # POST /api/ask
│   │   ├── library.py       # GET /api/library
│   │   ├── pdf.py           # PDF serving
│   │   └── health.py        # Health check
│   ├── adapters/            # Port implementations
│   │   ├── embed_openai.py  # OpenAI embedder
│   │   ├── vector_postgres.py # pgvector store
│   │   ├── llm_openai.py    # OpenAI LLM
│   │   └── rerank_openai.py # OpenAI reranker
│   └── services/            # Business logic
│       ├── qa.py            # Native QA pipeline
│       ├── prompting.py     # Persona prompts
│       └── formatting.py    # Citation formatting
├── rag/                      # RAG Core
│   ├── graph.py             # LangGraph RAG pipeline
│   ├── nodes/               # LangGraph node functions
│   │   ├── state.py         # RAGState TypedDict
│   │   ├── retrieve.py      # Document retrieval
│   │   ├── grade.py         # Relevance grading
│   │   ├── rewrite.py       # Query rewriting
│   │   ├── rerank.py        # Result reranking
│   │   ├── generate.py      # Answer generation
│   │   └── evaluate.py      # Hallucination check
│   ├── chain.py             # Legacy LCEL chain (fallback)
│   ├── ingest_lib/          # Ingestion utilities
│   │   ├── parser_azure.py  # Azure DI parser
│   │   ├── chunk_bbox_mapper.py # Bbox mapping
│   │   └── discover.py      # PDF discovery
│   └── retrieval/           # Retrieval utilities
│       ├── utils.py         # Hit preparation
│       └── pdf_links.py     # PDF resolution
├── frontend/                 # Next.js Frontend
│   └── src/
│       ├── app/             # Pages (chat, library)
│       └── components/      # UI components
├── configs/                  # YAML configs
│   ├── runtime/openai.yaml  # Runtime config
│   └── ingestion/           # Ingestion config
├── data/                     # Data storage
│   └── raw/                 # Source PDFs
└── docker-compose.yml        # PostgreSQL service
```

---

## Configuration

### Runtime Config (`configs/runtime/openai.yaml`)
Controls model selection, retrieval parameters, and LangChain settings.

```yaml
embedder:
  model: text-embedding-3-large
llm:
  model: gpt-4o
  temperature: 0.2
retrieval:
  k: 6
  mode: dense
  rerank: true
```

### Environment Variables (`.env`)
```bash
OPENAI_API_KEY=sk-...
POSTGRES_CONNECTION_STRING=postgresql+psycopg2://...
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
```

---

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| API Entry | `app/main.py` | FastAPI app with routers |
| Pipeline Factory | `app/factory.py` | Builds QA pipeline from YAML |
| Q&A Endpoint | `app/routers/ask.py` | Handles `/api/ask` requests |
| Vector Store | `app/adapters/vector_postgres.py` | Hybrid search with pgvector |
| **LangGraph Pipeline** | `rag/graph.py` | Corrective RAG with grading, rewriting, evaluation |
| RAG State | `rag/nodes/state.py` | Typed state flowing through pipeline |
| Azure Parser | `rag/ingest_lib/parser_azure.py` | PDF parsing with bbox extraction |
| Prompts | `app/services/prompting.py` | Persona-aware system prompts |
