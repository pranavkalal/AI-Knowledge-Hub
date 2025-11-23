# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: RAG Pipeline & Web Application
# -------------------------------

.PHONY: help install dev api ui ingest reindex clean test fmt

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install backend and frontend dependencies"
	@echo "  make dev        - Run both Backend and Frontend in parallel"
	@echo "  make api        - Run Backend API only (port 8000)"
	@echo "  make ui         - Run Frontend UI only (port 3000)"
	@echo "  make ingest     - Run robust batched PDF ingestion"
	@echo "  make reindex    - Rebuild FAISS index from existing chunks"
	@echo "  make clean      - Clean up temporary files and caches"
	@echo "  make test       - Run backend tests"
	@echo "  make fmt        - Format code (ruff)"

# -------------------------------
# Installation
# -------------------------------
install:
	@echo "📦 Installing Backend Dependencies..."
	pip install -r requirements.txt
	@echo "📦 Installing Frontend Dependencies..."
	cd frontend && npm install

# -------------------------------
# Development (Parallel Launch)
# -------------------------------
dev:
	@echo "🚀 Launching AI Knowledge Hub..."
	@# Run api and ui in parallel. Requires 'make -j2 dev' usually, but we can force it with &
	@trap 'kill 0' EXIT; \
	make api & \
	make ui & \
	wait

api:
	@echo "🔌 Starting FastAPI Backend..."
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	@echo "💻 Starting Next.js Frontend..."
	cd frontend && npm run dev

# -------------------------------
# Data Pipeline
# -------------------------------
ingest:
	@echo "📄 Starting Batched Ingestion..."
	python scripts/ingestion/run_batched.py

reindex:
	@echo "🔍 Rebuilding Search Index..."
	python -m scripts.indexing.build_embeddings --chunks data/staging/chunks.jsonl --out_vecs data/embeddings/embeddings.npy --out_ids data/embeddings/ids.npy --model text-embedding-3-small --adapter openai --batch 256 --normalize
	python scripts/indexing/build_faiss.py --embeddings data/embeddings/embeddings.npy --ids data/embeddings/ids.npy --out_index data/index/faiss.index

# -------------------------------
# Maintenance
# -------------------------------
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf frontend/.next frontend/node_modules/.cache
	find . -name "*.pyc" -delete

fmt:
	ruff check . --fix
	ruff format .

test:
	pytest tests/
