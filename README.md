# AI-Knowledge-Hub (CRDC Capstone Project)

This repo is the **skeleton** for our CRDC Knowledge Hub prototype.  
Right now it ingests a few **toy documents**, embeds them, stores vectors in **FAISS**, and runs a basic retrieval sanity check.

---

## Project Layout
app/ # Scripts to run ingestion and sanity checks
rag/ # Core retrieval components (embeddings, chunking, extraction)
store/ # Vector database (FAISS index files go here, gitignored)
configs/ # YAML configs for sources, ingestion params
data/ # Raw files, toy docs, staging outputs
tests/ # Sanity queries and small test scripts# AI-Knowledge-Hub
A web-based GenAI portal for CRDC to summarize and track R&amp;D investments across structured and unstructured data.

## Environment Setup
We’re pinned to **Python 3.11** (3.13 breaks FAISS).  

``bash
# create virtual env
python -m venv .venv311
source .venv311/bin/activate

# install dependencies
pip install -r requirements.txt

# Demo Run
With toy docs loaded, you can run:
python app/sanity.py

requirements.txt explained
numpy → core numeric ops
sentence-transformers / transformers / tokenizers / torch / accelerate → embedding stack (MiniLM, BERT, etc.)
faiss-cpu → vector search index (fast similarity search)
rich → nicer console output for debugging/logging

# Workflow (Pilot)
1. Ingestion
Discover – list candidate documents (later: crawl Inside Cotton library).
Extract – download/parse PDFs into text + metadata.
Normalize – clean text, keep page refs.
Chunk – split text into manageable windows.
Embed – generate vector representations with sentence-transformers.
Index – add vectors to FAISS.
Verify – run sanity queries to confirm retrieval quality.

3. Storage
Raw PDFs → data/raw/ (ignored by git).
Extracted text + metadata → data/staging/.
Vector index → store/faiss/.
Manifests → CSV/JSON with doc metadata.

5. Retrieval
At query time:
Embed the query → vector
Search FAISS for nearest chunks
Return text with cosine similarity score + metadata (title, year, page)
Eventually: pass chunks to LLM for summarization/answers with citations.

Expected:
Embeds toy docs
Stores them in FAISS
Answers a sample query (e.g. “Which 2024 projects focused on water use efficiency?”)
Prints top hit + score

Collaboration Strategy
main → protected, stable code only
dev → integration branch
feat/<feature>-<name> → individual work branches
Always PR into dev, merge into main only when demo-ready

Roadmap
Week 1–2: Ingest ~30 CRDC reports (2022–2024), FAISS index, demo retrieval
Next: Add Postgres for metadata (Phase 1), then pgvector for unified search (Phase 2)

Notes for Us
Don’t commit large PDFs or FAISS index files — they’re gitignored.
Keep configs editable (chunk sizes, rate limits).
Tests should include sample queries + expected doc hits.
