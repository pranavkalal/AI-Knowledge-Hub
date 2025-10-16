# AI Knowledge Hub

> Retrieval-augmented research assistant for the Cotton Research & Development Corporation (CRDC).
> Finds, cites, and explains answers hidden inside multi-year technical reports.

---

## Why it matters

- CRDC has decades of PDF research artefacts that are hard to search, quote, or defend in meetings.
- Scientists need **grounded** answers with citations they can stand behind.
- The Hub automates ingestion → indexing → retrieval so decisions happen faster than document hunts.

---

## Highlights

- **Structured RAG** – LangChain chain with JSON-schema answers, inline `[S#]` citations, and resilient fallbacks (ChatOpenAI → backup → local adapter → native QA pipeline).
- **Deep retrieval controls** – FAISS dense search with multi-query rewrites, contextual compression, and OpenAI-based reranking. Candidate pool tuning + timing telemetry built in.
- **Production plumbing** – Invoke tasks, regression harness (`invoke regress-langchain`), and config/env overrides you can ship.
- **UI + API parity** – Streamlit front end and FastAPI share the same orchestration layer.

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

## Everyday commands

```bash
invoke ingest                 # crawl & parse PDFs (configurable)
invoke chunk                  # chunk docs → staging/chunks.jsonl
invoke embed                  # build embeddings.npy + ids.npy
invoke faiss                  # build vectors.faiss index
invoke query -q "..."         # CLI retrieval check
invoke regress-langchain      # compare recall/latency before vs after
```

Runtime tweaks via env:
- `LC_USE_MULTIQUERY`, `LC_USE_COMPRESSION`, `LC_CANDIDATE_LIMIT`, `LC_CANDIDATE_MULTIPLIER`, `LC_CANDIDATE_MIN`
- `LC_USE_CHAT_OPENAI`, `LC_CHAT_BACKUP_MODEL`

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
| Tooling | Invoke, regression scripts | CI-friendly recall/latency checks |

Chunking stitches neighbour windows so citations provide enough context. Metadata tracks page numbers, file paths, and snippet lengths for prompt construction and future PDF highlighting.

---

## Documentation

| Topic | File |
|-------|------|
| System + runtime requirements | `docs/requirements.md`
| Deployment guide (API, UI, environments) | `docs/deployment.md`
| Architecture overview | `docs/architecture.md`
| LangChain orchestration & schema | `docs/orchestration.md`
| Ingestion pipeline & config keys | `docs/ingestion.md`
| Evaluation & regression workflows | `docs/evaluation.md`

---

## Next steps

- Clickable citations that open PDFs at the highlighted chunk
- Robust OCR + layout parsing for table-heavy, two-column reports
- Multimodal retrieval experiments (images + text)

If you’re evaluating the system or the team behind it, skim the docs above or run `invoke dev` for a quick tour.
