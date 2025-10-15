# 🧠 AI-Knowledge-Hub

> Modular GenAI system that transforms unstructured research reports into searchable, summarised insights — powered by retrieval-augmented generation (RAG), vector search, and flexible LLM orchestration.

### Overview

AI-Knowledge-Hub streamlines how organisations access decades of scattered research data.  
It automates:

- **Ingestion** of PDFs directly from source sites  
- **Extraction** of clean text + metadata  
- **Indexing** with dense embeddings (BGE-small-en-v1.5)  
- **Retrieval-Augmented Q&A** with inline citations  
- **Swappable orchestration** between Native Python ports and LangChain

For the detailed architecture report, see [`docs/AI-Knowledge-Hub-Overview.pdf`](./docs/AI-Knowledge-Hub-Overview.pdf).

---

## ⚙️ Requirements

| Component | Version | Purpose |
|------------|----------|----------|
| **Python** | 3.10 + | Core runtime |
| **Ollama** | 0.1.32 + | Local LLMs (install + model pull) |
| **pip** | latest | Dependency installer |
| **FAISS** | via `requirements.txt` | Vector index |
| **Git** | any recent | Repo management |

Optional: `make` (macOS/Linux). Windows users can run everything with `invoke`.

---

## 🚀 Quickstart

### 1. Clone and Set Up

```bash
git clone https://github.com/your-org/AI-Knowledge-Hub.git
cd AI-Knowledge-Hub
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Ollama (if you haven’t already)

macOS / Linux:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Windows (PowerShell):

```powershell
winget install Ollama.Ollama
```

Start the Ollama service once so it can finish bootstrapping, then keep it running in the background.

### 3. Pull the Default Model (llama3 by default)

```bash
ollama pull llama3
ollama list
```

> Want a different model? Replace `llama3` with any compatible Ollama model name and update `OLLAMA_MODEL` in `.env`.

### 4. Environment Variables

Create .env and then copy contents from .env.example to .env

## 🧩 Running the Pipeline

All automation is handled by Invoke tasks.
List them:

```bash
invoke --list
```

### Full Build

```bash
invoke build
```

Development Mode (API + UI)

```bash
invoke dev
```

API → http://localhost:8000/docs
UI → http://localhost:8501

Example Query

```bash
invoke query -q "How does soil management affect water use efficiency?"
```

### LangChain Retrieval Controls

- **Candidate pool** is controlled via `retrieval.candidate_multiplier`, `candidate_min`, and `candidate_overfetch_factor` in `configs/runtime/default.yaml`. Set `retrieval.candidate_limit` to hard-cap the pool.  
- Toggle rewrites and compression with `retrieval.use_multiquery` / `retrieval.use_compression`.  
- Runtime overrides from `.env` / shell:
  - `LC_USE_MULTIQUERY=1` or `LC_USE_COMPRESSION=1`
  - `LC_CANDIDATE_LIMIT`, `LC_CANDIDATE_MULTIPLIER`, `LC_CANDIDATE_MIN`, `LC_CANDIDATE_OVERFETCH_FACTOR`
  - `LC_USE_CHAT_OPENAI=1` and optional `LC_CHAT_BACKUP_MODEL=gpt-4o-mini`

When `langchain.use_chat_openai` is true, the chain now wraps ChatOpenAI in automatic fallbacks (`backup_model` → adapter LLM → native `QAPipeline`) so rate-limit spikes degrade gracefully. See `docs/orchestration.md` for a deeper walkthrough of the prompt schema and fallback graph.

### Regression Guardrail

Compare retrieval accuracy/latency before and after a change using the new Invoke task:

```bash
invoke regress-langchain --after configs/runtime/default.yaml --out reports/regression.json
```

By default the task uses `configs/runtime/openai.yaml` as the baseline and the current `COTTON_RUNTIME` as the candidate. The underlying script (`scripts/retrieval/regress.py`) emits hit-rate, MRR, precision@1, stage timings, and delta values.
