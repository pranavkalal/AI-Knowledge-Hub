# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: Make targets for ingestion, processing, embeddings, retrieval, and API
# -------------------------------

# Variables
Q ?= water efficiency in irrigated cotton
K ?= 5
N ?= 2  # neighbors

# -------------------------------
# Data Pipeline
# -------------------------------
# Makefile (Windows-friendly)

SHELL := cmd.exe
.SHELLFLAGS := /C

.PHONY: ingest eval.extract clean-extract chunk chunk-stats embed faiss query
.PHONY: ingest eval.extract clean-extract chunk chunk-stats

ingest:
	powershell -NoProfile -ExecutionPolicy Bypass -Command "if (!(Test-Path 'logs')) { New-Item -ItemType Directory -Path 'logs' | Out-Null }; $$log = 'logs/ingest_{0}.log' -f (Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'); python -m app.ingest --config configs/ingestion.yaml 2>&1 | Tee-Object -FilePath $$log -Append"

eval.extract:
	python -m app.extraction_eval

clean-extract:
	python -m app.clean_extract --in data/staging/docs.jsonl --out data/staging/cleaned.jsonl

chunk:
	python -m app.chunk --in data/staging/cleaned.jsonl --out data/staging/chunks.jsonl

chunk-stats:
	python tests/chunk_stats.py --in data/staging/chunks.jsonl

embed:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_embeddings --chunks data/staging/chunks.jsonl

faiss:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_faiss --vecs data/embeddings/embeddings.npy

query:
	PU=.; PYTHONPATH=$$PU python -m scripts.query_faiss --q "$(Q)" --k $(K) --per-doc 1 --neighbors $(N)

# -------------------------------
# API
# -------------------------------

.PHONY: api api-prod

# Dev server with auto-reload
api:
	python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

# Simple “prod-like” run (multi-worker, no reload)
api-prod:
	python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --workers 2

# Ruff does lint checks and auto-fixes, then reformats code.
fmt:
	ruff check . --fix
	ruff format .

# ---------- Run tests ----------
# Run pytest quietly (-q), using project root as PYTHONPATH so app/ imports work.
test:
	PYTHONPATH=. pytest -q