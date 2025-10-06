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
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH = '.'; python -m scripts.build_embeddings --chunks '$(CHUNKS)'"
else
	PYTHONPATH=. $(PY) -m scripts.build_embeddings --chunks $(CHUNKS)
endif

faiss:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; python -m scripts.build_faiss --vecs '$(EMBEDS)' --index_out '$(INDEX)'"
else
	PYTHONPATH=. $(PY) -m scripts.build_faiss --vecs $(EMBEDS) --index_out $(INDEX)
endif


# Guarded query (forces Q and passes through ARGS)
query:
ifeq ($(OS),Windows_NT)
	@if "$(Q)"=="" ( echo Usage: make query Q="your text" K=8 N=2 PER_DOC=2 ARGS="--year-min 2015" & exit 1 ) else powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; python -m scripts.query_faiss --q '$(Q)' --k $(K) --per-doc $(PER_DOC) --neighbors $(N) $(ARGS)"
else
	@if [ -z "$(Q)" ]; then echo 'Usage: make query Q="your text" K=8 N=2 PER_DOC=2 ARGS="--year-min 2015"'; exit 1; fi
	PYTHONPATH=. $(PY) -m scripts.query_faiss --q "$(Q)" --k $(K) --per-doc $(PER_DOC) --neighbors $(N) $(ARGS)
endif




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

ifeq ($(OS),Windows_NT)
  PY := python
  RUN_PY := powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; python"
  RUN := powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; "
else
  PY := python3
  RUN_PY := PYTHONPATH=. python3
  RUN := PYTHONPATH=.
endif

UVICORN ?= uvicorn
STREAMLIT ?= streamlit
HOST ?= 0.0.0.0
PORT ?= 8000
UI_PORT ?= 8501
COTTON_API_BASE ?= http://localhost:$(PORT)/api

.PHONY: api ui dev stop-api

api:
ifeq ($(OS),Windows_NT)
	$(RUN) $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload
else
	PYTHONPATH=. $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload
endif

ui:
ifeq ($(OS),Windows_NT)
	$(RUN) $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT)
else
	COTTON_API_BASE=$(COTTON_API_BASE) PYTHONPATH=. $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT)
endif

# Simple cross-platform 'dev' runner
dev:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; Start-Process -FilePath '$(PY)' -ArgumentList '-m','$(UVICORN)','app.main:app','--host','$(HOST)','--port','$(PORT)','--reload' -PassThru | Set-Content .api.pid; $$env:COTTON_API_BASE='$(COTTON_API_BASE)'; $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT)"
else
	PYTHONPATH=. $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload & \
	echo $$! > .api.pid; \
	COTTON_API_BASE=$(COTTON_API_BASE) PYTHONPATH=. $(STREAMLIT) run ui/streamlit_app.py --server.port $(UI_PORT); \
	kill $$(cat .api.pid) 2>/dev/null || true; rm -f .api.pid
endif

stop-api:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path .api.pid) { Get-Content .api.pid | % { try { Stop-Process -Id $$_ -Force } catch {} }; Remove-Item .api.pid -Force }"
else
	-kill $$(cat .api.pid) 2>/dev/null || true; rm -f .api.pid
endif


# ---------- OCR toolchain check ----------
.PHONY: verify-ocr
verify-ocr:
	$(PYTHON) - <<'PYCODE'
import importlib, subprocess, sys
mods = ["fitz", "pdfplumber", "PIL", "pytesseract"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    print("Missing Python modules:", ", ".join(missing))
    sys.exit(1)
try:
    out = subprocess.check_output(["tesseract","--version"]).decode().splitlines()[0]
    print("Tesseract:", out)
    print("OCR toolchain looks OK.")
except Exception as e:
    print("Could not invoke 'tesseract' on PATH:", e)
    sys.exit(2)
PYCODE

# ---------- Windows-friendly API (fixes PYTHONPATH issue on PowerShell) ----------
.PHONY: api-win
api-win:
	powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PYTHONPATH='.'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
