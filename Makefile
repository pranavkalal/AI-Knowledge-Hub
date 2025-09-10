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

.PHONY: ingest eval.extract clean-extract chunk chunk-stats embed faiss query

ingest:
	mkdir -p logs
	python -m app.ingest --config configs/ingestion.yaml 2>&1 | tee logs/ingest_$$(date +%F_%H-%M-%S).log

eval.extract:
	python -m app.extraction_eval

clean-extract:
	python -m app.clean_extract --in data/staging/docs.jsonl --out data/staging/cleaned.jsonl

chunk:
	python -m app.chunk --in data/staging/cleaned.jsonl --out data/staging/chunks.jsonl

chunk-stats:
	python sanity_scripts/chunk_stats.py --in data/staging/chunks.jsonl

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
