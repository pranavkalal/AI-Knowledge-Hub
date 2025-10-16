# AI Knowledge Hub

> Retrieval-augmented research assistant for the Cotton Research & Development Corporation (CRDC).
> Finds, cites, and explains answers hidden inside multi-year technical reports.

---

## Why it matters

- Growers need practical, evidence-backed insights without trawling hundreds of pages.
- Researchers must surface the right paragraph, page, and citation to defend recommendations.
- CRDC teams can focus on decisions, not document hunts, because the hub keeps knowledge stitched together.

---

## Quick start

```bash
# 1. Clone & install
git clone https://github.com/your-org/AI-Knowledge-Hub.git
cd AI-Knowledge-Hub
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure runtime (OpenAI preset by default)
cp .env.example .env   # add API keys, tweak COTTON_RUNTIME, etc.

# 3. Build the corpus (ingest → chunk → embed → index)
invoke build

# 4. Run API + Streamlit UI
invoke dev
# API: http://localhost:8000/docs
# UI:  http://localhost:8501
```

> Need Ollama, GPU OCR, or alternative embeddings? See `docs/requirements.md`.

---

## Tech stack snapshot

| Layer | Tooling | Notes |
|-------|---------|-------|
| Orchestration | LangChain (`rag/chain.py`) | Structured outputs, fallback runnables |
| Retrieval | FAISS dense index | Configurable candidate pool + telemetry |
| Embeddings | OpenAI or BGE (config-based) | Cosine scoring, chunk metadata retained |
| Reranker | OpenAI embedding reranker | Pool stats + latency logging |
| Ingestion | Custom crawler + OCR-ready parsing | YAML-driven sources, skip lists, retry logic |
| Front end | Streamlit + FastAPI | Shared chain wrapper keeps answers consistent |
| LLMs | OpenAI Chat models (plus local adapters) | Structured JSON answers, fallback stack |
| Tooling | Invoke, regression scripts | CI-friendly recall/latency checks |

Chunking stitches neighbour windows so citations provide enough context. Metadata tracks page numbers, file paths, and snippet lengths for prompt construction and future PDF highlighting.

---

## Highlights

- **Structured answers for researchers & growers** – The UI surfaces cited summaries, key points, and conclusions in language stakeholders can act on quickly.
- **Configurable retrieval depth** – Multi-query expansion, compression, and reranking help surface agronomic nuance buried in long reports.
- **Traceable answers** – Inline citations jump back to source passages (PDF highlighting planned in the next phase).

---

## Documentation

| Topic | File |
|-------|------|
| System + runtime requirements | `docs/requirements.md` |
| Deployment guide (API, UI, environments) | `docs/deployment.md` |
| Architecture overview | `docs/architecture.md` |
| LangChain orchestration & schema | `docs/orchestration.md` |
| Ingestion pipeline & config keys | `docs/ingestion.md` |
| Evaluation & regression workflows | `docs/evaluation.md` |

---

## Next steps

- Evolve from standard dense RAG to **GraphRAG** for richer cross-report reasoning.
- Plug in structured agronomy data and support multiple personas (researchers, growers, policy teams).
- Add conversational memory so returning users build on prior sessions.
- Harden cloud deployment (container images, managed vector DB, observability stack).
