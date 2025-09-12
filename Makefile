# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: Make targets for ingestion, processing, embeddings, retrieval, and API
# -------------------------------

# Variables (defaults you can override at call time)
# Do NOT default Q to a real query; force the user to pass it.
Q ?=
K ?= 5
N ?= 2        # neighbors
per_doc ?= 2  # per-document diversification
ARGS ?=

.PHONY: ingest eval.extract clean-extract chunk chunk-stats embed faiss query api api-prod fmt test help

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
	python tests/chunk_stats.py --in data/staging/chunks.jsonl

embed:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_embeddings --chunks data/staging/chunks.jsonl

faiss:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_faiss --vecs data/embeddings/embeddings.npy

# Query the index
query:
	@if [ -z "$(Q)" ]; then \
	  echo 'Usage: make query Q="your text" K=8 N=2 per_doc=2 ARGS="--year-min 2015 --contains herbicide"'; \
	  exit 1; \
	fi
	@echo "QUERY: $(Q)"
	PU=.; PYTHONPATH=$$PU python -m scripts.query_faiss \
	  --q "$(Q)" \
	  --k $(K) \
	  --per-doc $(per_doc) \
	  --neighbors $(N) \
	  $(ARGS)

# API
api:
	python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

api-prod:
	python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --workers 2

# Formatting
fmt:
	ruff check . --fix
	ruff format .

# Tests
test:
	PYTHONPATH=. pytest -q

help:
	@echo 'Examples:'
	@echo '  make query Q="Grazon Extra impact on cotton yield" K=8 N=2 per_doc=2 ARGS="--year-min 2010 --contains \"grazon extra,herbicide\" "'
	@echo '  make query Q="Flame herbicide off-target effects" ARGS="--contains flame"'
