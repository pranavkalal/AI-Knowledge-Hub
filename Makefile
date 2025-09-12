# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: Make targets for ingestion, processing, embeddings, retrieval, and API
# -------------------------------

# -------- Defaults (tweak as needed)
Q ?= water efficiency in irrigated cotton
K ?= 5
N ?= 2            # neighbors
PER_DOC ?= 2
CHUNKS ?= data/staging/chunks.jsonl
EMBEDS ?= data/embeddings/embeddings.npy
INDEX ?= data/embeddings/vectors.faiss

# -------- Cross-platform shims
ifeq ($(OS),Windows_NT)
  # Windows
  SHELL := cmd.exe
  .SHELLFLAGS := /C
  PY := python
  MKDIR := powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path"
  TEE := powershell -NoProfile -Command "Tee-Object -FilePath"
  NOW := powershell -NoProfile -Command "(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
  QUOTE :=
else
  # macOS / Linux
  SHELL := /bin/bash
  .SHELLFLAGS := -c
  PY := python3
  MKDIR := mkdir -p
  TEE := tee
  NOW := $(shell date "+%Y-%m-%d_%H-%M-%S")
  QUOTE := "
endif

.PHONY: ingest eval.extract clean-extract chunk chunk-stats embed faiss query api api-prod fmt test

# -------------------------------
# Data Pipeline
# -------------------------------

ingest:
ifeq ($(OS),Windows_NT)
	@if not exist logs $(MKDIR) logs
	@set LOG=logs\ingest_$($(NOW)).log && \
	$(PY) -m app.ingest --config configs/ingestion.yaml 2>&1 | powershell -NoProfile -Command "$$input | Tee-Object -FilePath $$env:LOG -Append" 
else
	$(MKDIR) logs
	$(PY) -m app.ingest --config configs/ingestion.yaml 2>&1 | $(TEE) logs/ingest_$(NOW).log
endif

eval.extract:
	$(PY) -m app.extraction_eval

clean-extract:
	$(PY) -m app.clean_extract --in data/staging/docs.jsonl --out data/staging/cleaned.jsonl

chunk:
	$(PY) -m app.chunk --in data/staging/cleaned.jsonl --out $(CHUNKS)

chunk-stats:
	$(PY) tests/chunk_stats.py --in $(CHUNKS)

embed:
	PU=. PYTHONPATH=$$PU $(PY) -m scripts.build_embeddings --chunks $(CHUNKS)

faiss:
	PU=. PYTHONPATH=$$PU $(PY) -m scripts.build_faiss --vecs $(EMBEDS) --out $(INDEX)

query:
	PU=. PYTHONPATH=$$PU $(PY) -m scripts.query_faiss --q $(QUOTE)$(Q)$(QUOTE) --k $(K) --per-doc $(PER_DOC) --neighbors $(N)

# -------------------------------
# API
# -------------------------------

api:
	$(PY) -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

api-prod:
	$(PY) -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --workers 2

# -------------------------------
# Tooling
# -------------------------------

fmt:
	ruff check . --fix
	ruff format .

test:
	PYTHONPATH=. pytest -q
