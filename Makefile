# -------------------------------
#  Project: AI Knowledge Hub
#  Purpose: ingestion, embeddings, FAISS, retrieval, API
# -------------------------------

# -------- Defaults (override at call time)
Q ?=
K ?= 5
N ?= 2                 # neighbors
PER_DOC ?= 2           # per-doc diversification
CHUNKS ?= data/staging/chunks.jsonl
EMBEDS ?= data/embeddings/embeddings.npy
INDEX  ?= data/embeddings/vectors.faiss
ARGS   ?=

# -------- Cross-platform shims
ifeq ($(OS),Windows_NT)
  SHELL := cmd.exe
  .SHELLFLAGS := /C
  PY := python
  MKDIR := powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path"
  TEE := powershell -NoProfile -Command "Tee-Object -FilePath"
  NOW := powershell -NoProfile -Command "(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
  QUOTE :=
else
  SHELL := /bin/bash
  .SHELLFLAGS := -c
  PY := python3
  MKDIR := mkdir -p
  TEE := tee
  NOW := $(shell date "+%Y-%m-%d_%H-%M-%S")
  QUOTE := "
endif

.PHONY: ingest eval.extract clean-extract chunk chunk-stats embed faiss query api api-prod fmt test help

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
	PU=. PYTHONPATH=$$PU $(PY) -m scripts.build_faiss --vecs $(EMBEDS) --index_out $(INDEX)


# Guarded query (forces Q and passes through ARGS)
query:
	@if [ -z "$(Q)" ]; then \
	  echo 'Usage: make query Q="your text" K=8 N=2 PER_DOC=2 ARGS="--year-min 2015 --contains herbicide"'; \
	  exit 1; \
	fi
	@echo "QUERY: $(Q)"
	PU=. PYTHONPATH=$$PU $(PY) -m scripts.query_faiss \
	  --q $(QUOTE)$(Q)$(QUOTE) \
	  --k $(K) \
	  --per-doc $(PER_DOC) \
	  --neighbors $(N) \
	  $(ARGS)




# -------------------------------
# Tooling
# -------------------------------

fmt:
	ruff check . --fix
	ruff format .

test:
	PYTHONPATH=. pytest -q

help:
	@echo 'Examples:'
	@echo '  make query Q="Grazon Extra impact on cotton yield" K=8 N=2 PER_DOC=2 ARGS="--year-min 2010 --contains \"grazon extra,herbicide\" "'
	@echo '  make query Q="pyriproxyfen spray window"'

# -------------------------------
# API
# -------------------------------

.PHONY: api api-prod ui dev stop-api ask.demo ask QJSON

PY ?= python3
UVICORN ?= uvicorn
STREAMLIT ?= streamlit
HOST ?= 0.0.0.0
PORT ?= 8000
UI_PORT ?= 8501
COTTON_API_BASE ?= http://localhost:$(PORT)/api

api:
	PYTHONPATH=. $(PY) -m $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

ui:
	COTTON_API_BASE=$(COTTON_API_BASE) $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT)

# one-shot developer runner: starts API in bg, runs UI, cleans up API on exit
dev:
	PYTHONPATH=. $(PY) -m $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload & \
	echo $$! > .api.pid; \
	COTTON_API_BASE=$(COTTON_API_BASE) $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT); \
	kill $$(cat .api.pid) 2>/dev/null || true; rm -f .api.pid

stop-api:
	-kill $$(cat .api.pid) 2>/dev/null || true; rm -f .api.pid

# fixed ask demo (quotes escaped for Makefiles)
ask.demo:
	@curl -s http://localhost:$(PORT)/api/ask \
		-H "Content-Type: application/json" \
		-d "{\"question\":\"Summarise post-2018 water productivity trends with citations.\", \"k\":5}" | jq

# parametric ask target: pass Q='your question' and optional K=#
Q ?=
K ?= 6
ask:
	@if [ -z "$(Q)" ]; then echo 'Usage: make ask Q="your question" K=6'; exit 1; fi
	@curl -s http://localhost:$(PORT)/api/ask \
		-H "Content-Type: application/json" \
		-d "$$(jq -nc --arg q "$(Q)" --argjson k $(K) '{question:$$q, k:$$k}')" | jq




