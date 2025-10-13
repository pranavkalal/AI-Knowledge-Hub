# AI Knowledge Hub Architecture

## Code Map
| Directory | Key files/modules | Purpose |
| --- | --- | --- |
| . | Makefile; tasks.py; requirements.txt; README.md; API_CONTRACT.md | Build/test automation, Invoke orchestration, dependency pinning, and client-facing documentation |
| app/ | main.py; factory.py; ingest.py; clean_extract.py; chunk.py; extraction_eval.py; setting.py | FastAPI entrypoint, pipeline factory, ingestion/cleaning CLIs, extraction audit, and shared settings |
| app/adapters/ | embed_bge.py; vector_faiss.py; llm_openai.py; llm_ollama.py; rerank_bge.py; rerank_noop.py | Ports-compliant adapters for embeddings, vector store, LLM providers, and reranking strategies |
| app/services/ | qa.py; prompting.py; formatting.py | Native question-answer pipeline, prompt templates, and citation/snippet formatting helpers |
| app/service/ | search_service.py | Direct FAISS retrieval service reused by `/api/search` and CLI tools |
| app/routers/ | ask.py; search.py; pdf.py; health.py | HTTP API surface for Q&A, search, PDF serving, and health checks |
| app/schemas.py | SearchResponse; SearchResult | Pydantic response contracts for search endpoints |
| app/ports.py | EmbedderPort; VectorStorePort; RerankerPort; LLMPort | Protocol interfaces that define the adapter contracts |
| rag/ | chain.py; router_chain.py; langchain_adapters.py; callbacks.py | LangChain orchestration graph, question router prototype, LC retriever wrapper, and tracing callbacks |
| rag/ingest_lib/ | discover.py; download.py; parse_pdf.py; store.py | Crawl InsideCotton, download PDFs, extract text/metadata, and persist JSONL/CSV outputs |
| rag/extract/ | pipeline.py; cleaners.py | JSONL IO helpers and text cleaning pipeline applied post-ingest |
| rag/segment/ | chunker.py | Token-aware chunking and offset bookkeeping |
| rag/embed/ | embedder.py | SentenceTransformer wrapper used by embedding adapter |
| rag/retrieval/ | utils.py; pdf_links.py | Retrieval filters, preview stitching, and PDF filename resolution |
| scripts/ | build_embeddings.py; build_faiss.py; query_faiss.py; eval_retrieval.py | Offline batch jobs for embeddings/index, FAISS query CLI, and retrieval evaluation |
| store/ | store_faiss.py | Thin persistence wrapper around `faiss.IndexFlatIP` |
| ui/ | streamlit_app.py | Streamlit UX for asking questions and debugging retrieval |
| configs/ | ingestion.yaml; runtime.yaml | Ingestion seeds and runtime configuration for orchestrator/adapters |
| tests/ | test_pipeline_parity.py; test_lc_ports_retriever.py; test_query_cli.py; chunk_stats.py | Regression tests for pipeline parity, LC retriever behavior, CLI output, and chunk statistics utility |

## End-to-End Pipeline
1. **Discover & ingest PDFs** — `app/ingest.py` loads `configs/ingestion.yaml`, uses `rag.ingest_lib.*` to crawl seed URLs, download PDFs into `data/raw/`, and emit document-level `data/staging/docs.jsonl` plus `docs.csv`.
2. **Document cleaning (optional)** — `app/clean_extract.py` with `rag.extract.pipeline.clean_records` normalises text and filters short documents into `data/staging/cleaned.jsonl`.
3. **Chunking** — `app/chunk.py` and `rag.segment.chunker` tokenise and window content into overlapping records stored in `data/staging/chunks.jsonl`.
4. **Embedding build** — `scripts/build_embeddings.py` reuses `BGEEmbeddingAdapter` to encode chunks into `data/embeddings/embeddings.npy` with aligned `ids.npy`.
5. **Vector index** — `scripts/build_faiss.py` and `store.store_faiss.FaissFlatIP` convert embeddings into `data/embeddings/vectors.faiss`.
6. **Serving pipeline** — `app.factory.build_pipeline` wires adapters per `configs/runtime.yaml`, returning either the native `QAPipeline` (`app/services/qa.py`) or the LangChain graph (`rag/chain.py`).
7. **Interfaces** — FastAPI routers in `app/routers/` expose `/api/search` and `/api/ask`; `ui/streamlit_app.py` and CLI utilities (`scripts/query_faiss.py`) consume the same retrieval stack.

## Data Flow Diagram
```
          Seed URLs / PDFs (data/raw)
                   |
       app.ingest -- configs/ingestion.yaml
                   v
         data/staging/docs.jsonl
                   |
        app.clean_extract (optional)
                   v
         data/staging/cleaned.jsonl
                   |
              app.chunk
                   v
         data/staging/chunks.jsonl
                   |
 scripts.build_embeddings (BGEEmbeddingAdapter)
                   v
 data/embeddings/embeddings.npy + data/embeddings/ids.npy
                   |
   scripts.build_faiss (FaissFlatIP.save)
                   v
        data/embeddings/vectors.faiss
                   |
 app.factory.build_pipeline → FastAPI / Streamlit UI
```

## Entry Points & Commands
| Command | Description |
| --- | --- |
| `make ingest` | Crawl/download PDFs and write `data/staging/docs.jsonl` while teeing logs to `logs/`. |
| `make clean-extract` | Run `app.clean_extract` to produce `data/staging/cleaned.jsonl`. |
| `make chunk` | Execute `app.chunk` with configurable token/overlap settings into `data/staging/chunks.jsonl`. |
| `make embed` | Build `embeddings.npy` and `ids.npy` via `scripts.build_embeddings`. |
| `make faiss` | Create `vectors.faiss` from embeddings with `scripts.build_faiss`. |
| `make query Q="..."` | Ad-hoc FAISS query using `scripts.query_faiss` with filters/overfetch controls. |
| `make api` / `make ui` / `make dev` | Launch FastAPI, Streamlit, or both (with auto-shutdown) for local serving. |
| `make fmt` / `make test` | Run Ruff auto-fix + format, or Pytest suite. |
| `make ask` / `make ask.demo` | Curl-based smoke tests against `/api/ask`. |

| Invoke task | Description |
| --- | --- |
| `invoke build` | Full pipeline: ingest → clean → chunk → embed → faiss with guardrails for empty outputs. |
| `invoke ingest` / `clean-extract` / `chunk` | Individually run ingestion, cleaning, or chunking steps. |
| `invoke embed` / `faiss` | Batch embedding and FAISS index creation with shared config/env wiring. |
| `invoke query` | Wrapper around `scripts.query_faiss` with toggleable metadata output. |
| `invoke api` / `ui` / `dev` | Start FastAPI, Streamlit, or both (ensuring index exists). |
| `invoke eval-extract` | Generate extraction audit CSV from `data/staging/docs.jsonl`. |
| `invoke eval.retrieval` | Compare native vs LangChain pipelines on evaluation queries. |
| `invoke clean` / `clobber` / `rebuild` | Remove staging artifacts, delete embeddings/index, or rebuild end-to-end. |

## Adapter Stack & Configuration
| Component | Default adapter | Implementation | Config knobs |
| --- | --- | --- | --- |
| Embeddings | `bge_local` | `app/adapters/embed_bge.BGEEmbeddingAdapter` wrapping `rag/embed/embedder.py` | `configs/runtime.yaml: embedder.model`, `EMB_MODEL` env var |
| Vector store | `faiss_local` | `app/adapters/vector_faiss.FaissStoreAdapter` loading `store/store_faiss.FaissFlatIP` | `runtime.yaml: vector_store.path`, `ids`, `meta`; `FAISS_*` env overrides |
| Reranker | `bge_reranker` (or `none`) | `app/adapters/rerank_bge.BGERerankerAdapter` or `NoopReranker` | `runtime.yaml: reranker.adapter`, `model`; optional `retrieval.rerank` toggle |
| LLM | `ollama` (default) or `openai` | `app/adapters/llm_ollama.OllamaAdapter` / `llm_openai.OpenAIAdapter` | `runtime.yaml: llm.adapter`, `model`, `temperature`, `max_output_tokens`; `OLLAMA_HOST` / OpenAI env credentials |
| Orchestrator | `langchain` | `rag/chain.build_chain` (async stream capable) or native `app/services/qa.QAPipeline` | `runtime.yaml: orchestrator`, `retrieval.k/mode/filters`, `langchain.stream/trace` |
| Retrieval filters | Ports retriever / utilities | `rag/langchain_adapters.PortsRetriever`, `rag/retrieval/utils.prepare_hits` | `runtime.yaml: retrieval.filters`, API query params, env defaults in `app/service/search_service.py` |

## Risky Assumptions & Missing Preconditions
- `app.factory._require_file` mandates that `data/embeddings/vectors.faiss`, `ids.npy`, and `data/staging/chunks.jsonl` already exist; the API will crash on startup if any artifact is missing or empty.
- Embedding builds must use the same model (and normalisation settings) configured at runtime; changing `embedder.model` without regenerating `embeddings.npy` yields meaningless similarity scores.
- `OllamaAdapter` assumes an Ollama daemon reachable at `OLLAMA_HOST` (default `http://localhost:11434`); timeouts surface as generic runtime errors.
- `OpenAIAdapter` relies on `OPENAI_API_KEY` (and related OpenAI env vars) being set; missing credentials trigger client creation failures at query time.
- Ingestion scrapers in `rag/ingest_lib.discover` assume current InsideCotton HTML structure and PDF availability; layout changes or rate limits can silently produce zero-doc pipelines.
- PDF routing (`app/routers/pdf.py`, `rag/retrieval/pdf_links.py`) depends on ingest metadata mapping doc IDs to filenames under `data/raw/`; manual PDF uploads must follow the hashed naming convention or `/pdf` links will 404.
- `FaissStoreAdapter` eagerly loads chunk metadata into memory; very large corpora may exceed memory limits and lack pagination/back-pressure controls.
- SentenceTransformer and CrossEncoder models download weights on first use; air-gapped deployments need pre-seeded caches or the embedding/reranker steps will fail.
