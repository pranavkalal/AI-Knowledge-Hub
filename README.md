# CRDC AI Knowledge Hub

AI-Enhanced Knowledge Hub for the Australian Cotton Industry - A modular RAG system that transforms 40+ years of cotton research into an intelligent, searchable knowledge base.

---

## Quick Start

```bash
# 1. Clone & Install
git clone https://github.com/your-org/AI-Knowledge-Hub.git
cd AI-Knowledge-Hub
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: Add your OPENAI_API_KEY

# 3. Ingest Documents (batched for stability)
python scripts/ingestion/run_batched.py

# 4. Run API Server
python -m app.main

# API Docs: http://localhost:8000/docs
```

---

## What It Does

- **Ingests** decades of cotton research PDFs using Docling (IBM's advanced PDF parser)
- **Chunks** documents semantically with OpenAI's tiktoken tokenizer
- **Embeds** using `text-embedding-3-small` for high-quality retrieval
- **Indexes** with FAISS for fast similarity search
- **Retrieves** with context stitching and optional reranking
- **Generates** evidence-based answers with GPT-4o-mini, including citations

---

## Repository Structure

```
AI-Knowledge-Hub/
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System design
│   ├── API_CONTRACT.md        # API specifications
│   └── LANGCHAIN_REVIEW.md    # LangChain analysis
│
├── scripts/                   # Production scripts
│   ├── ingestion/             # PDF → SQLite pipeline
│   │   ├── run_batched.py     # Main ingestion orchestrator
│   │   └── import_excel.py    # Import metadata from Excel
│   ├── indexing/              # Embeddings & FAISS
│   │   ├── build_embeddings.py
│   │   └── build_faiss.py
│   ├── evaluation/            # Quality metrics
│   └── utils/                 # Helper tools
│       └── verify_pipeline.py # End-to-end test
│
├── rag/                       # Core RAG logic
│   ├── ingest/                # Document processing
│   │   ├── parsers/           # Docling PDF parser
│   │   └── chunkers/          # Semantic chunking
│   ├── retrieval/             # Search utilities
│   ├── store/                 # SQLite database
│   └── chain.py               # LangChain orchestration
│
├── app/                       # FastAPI server
│   ├── adapters/              # Embedding, LLM, reranker
│   ├── routers/               # API endpoints
│   └── services/              # QA pipeline
│
├── frontend/                  # Next.js UI (optional)
│
├── data/
│   ├── raw/                   # PDF documents
│   ├── knowledge_hub.db       # SQLite (metadata + chunks)
│   └── embeddings/            # Vectors + FAISS index
│
└── tools/                     # Dev/debug utilities
```

---

## Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **PDF Parsing** | Docling (IBM) | Multi-modal: text, tables, images, bboxes |
| **Chunking** | Semantic (LangChain) | Token-aware, preserves structure |
| **Tokenizer** | tiktoken (OpenAI) | `cl100k_base` - matches embeddings |
| **Embeddings** | text-embedding-3-small | 1536 dims, high quality |
| **Vector Store** | FAISS | Fast approximate nearest neighbor |
| **Metadata** | SQLite | Chunks, documents, bboxes for deep linking |
| **LLM** | GPT-4o-mini | Structured outputs, citations |
| **Reranker** | text-embedding-3-large | Optional quality boost |
| **Orchestration** | LangChain (LCEL) | Composable chains, fallbacks |
| **API** | FastAPI | OpenAPI docs, async |
| **Frontend** | Next.js + shadcn/ui | Optional UI |

---

## Key Features

### 🔍 **Intelligent Retrieval**
- Hybrid search (dense + optional BM25)
- Context stitching (neighbor chunks for full context)
- Per-document diversity
- Configurable reranking

### 📚 **Deep Linking to PDFs**
- Bounding box coordinates stored in SQLite
- Direct links to exact page + position: `/pdf/by-id/{doc_id}#page=5`
- Frontend PDF viewer with highlight jumping

### 🎯 **Semantic Chunking**
- Respects document structure (sections → paragraphs → sentences)
- Overlap for context continuity
- Token-aware (matches embedding model)

### 🔧 **Production-Ready**
- Batched ingestion (prevents memory crashes)
- SQLite for metadata (scalable, ACID)
- Comprehensive logging
- Evaluation scripts

---

## Configuration

All settings in `.env` (see `.env.example`):

```bash
# Core
OPENAI_API_KEY=sk-...
EMB_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini

# Chunking
CHUNK_MAX_TOKENS=512
CHUNK_OVERLAP=128
USE_TIKTOKEN=1

# Ingestion
DOCLING_DEVICE=cpu  # Use 'mps' for Mac GPU (unstable)

# Retrieval
RETRIEVAL_K=6
RETRIEVAL_NEIGHBORS=1
```

---

## Usage Examples

### Ingest New PDFs
```bash
# 1. Place PDFs in data/raw/
# 2. Add metadata to SQLite (or use Excel import)
python scripts/ingestion/import_excel.py path/to/metadata.xlsx

# 3. Run batched ingestion
python scripts/ingestion/run_batched.py
```

### Query the API
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are best practices for cotton irrigation?"}'
```

### Verify Pipeline
```bash
python scripts/utils/verify_pipeline.py
```

---

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Lint
ruff check .

# Format
ruff format .
```

---

## Troubleshooting

**Ingestion crashes (CPU/RAM spike)?**
- Use batched ingestion: `run_batched.py` (processes 5 docs at a time)
- Set `DOCLING_DEVICE=cpu` in `.env` (disables MPS acceleration)

**No images extracted?**
- Check logs for `DEBUG: ITEM: label=...` to see actual Docling labels
- Docling might not detect images in scanned PDFs

**Import errors after reorganization?**
- Updated structure: `rag/ingest/parsers/`, `rag/ingest/chunkers/`
- Old imports from `rag/ingest_lib/` or `rag/segment/` will fail

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Acknowledgments

- **CRDC** for providing research data
- **IBM Docling** for advanced PDF parsing
- **OpenAI** for embeddings and LLMs
- **LangChain** for RAG orchestration
