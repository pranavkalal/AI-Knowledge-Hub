# 🧠 AI-Knowledge-Hub

> Modular GenAI system that transforms unstructured research reports into searchable, summarised insights — powered by retrieval-augmented generation (RAG), vector search, and flexible LLM orchestration.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)]()
[![FAISS](https://img.shields.io/badge/vectorstore-FAISS-green.svg)]()
[![LangChain](https://img.shields.io/badge/orchestrator-LangChain%20|%20Native-orange.svg)]()

---

### 📄 Overview

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
