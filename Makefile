# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: RAG Pipeline & Web Application
# -------------------------------

PYTHON=/Users/viking/.venv311/bin/python

.PHONY: help install dev api ui ingest clean test fmt

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install backend and frontend dependencies"
	@echo "  make dev        - Run both Backend and Frontend in parallel"
	@echo "  make api        - Run Backend API only (port 8000)"
	@echo "  make ui         - Run Frontend UI only (port 3000)"
	@echo "  make db         - Start PostgreSQL only (lightweight)"
	@echo "  make db-stop    - Stop PostgreSQL"
	@echo "  make ingest     - Run PDF ingestion (Azure + Postgres)"
	@echo "  make clean      - Clean up temporary files and caches"
	@echo "  make test       - Run backend tests"
	@echo "  make fmt        - Format code (ruff)"

# -------------------------------
# Installation
# -------------------------------
install:
	@echo "📦 Installing Backend Dependencies..."
	$(PYTHON) -m pip install -r requirements.txt
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
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	@echo "💻 Starting Next.js Frontend..."
	cd frontend && npm run dev

# -------------------------------
# Database (lightweight - Postgres only)
# -------------------------------
db:
	@echo "🗄️  Starting PostgreSQL (pgvector)..."
	docker-compose up -d db
	@echo "✅ Database ready on port 5432"

db-stop:
	@echo "🛑 Stopping PostgreSQL..."
	docker-compose stop db

# -------------------------------
# Data Pipeline
# -------------------------------
ingest:
	@echo "📄 Starting Azure/Postgres Ingestion..."
	PYTHONPATH=. $(PYTHON) app/ingest.py

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
