# LangChain Orchestration Overview

This document explains how the LangChain pathway is assembled after the refactor.

## Prompt schema

`rag/prompts/structured.py` centralises the templates and schema definitions used by the LangChain chain:

- `SYSTEM_PROMPT` – guardrails for the assistant.
- `PROMPT_USER_INSTRUCTIONS` – task-level instructions for summaries, key points, and conclusions.
- `STRUCTURED_FORMAT_INSTRUCTIONS` – JSON contract returned by the model.
- `StructuredAnswer` – Pydantic model used to validate JSON output.
- `prepare_prompt_state` – converts retrieved `Document` objects into the prompt state (citations, sources block, model temperature, etc.).
- `build_prompt_messages` – renders the `ChatPromptTemplate` as OpenAI-compatible messages, appending available citation IDs.
- `message_to_text` / `extract_usage` – utility helpers shared by fallbacks.
- `format_structured_answer` – produces the final human-readable markdown sections from the structured payload.

Because these live in a shared module, both the LangChain chain and any direct adapters (e.g., future FastAPI streaming endpoints) can depend on the same schema without importing the entire orchestration file.

## Chain construction

`rag/chain.py` now focuses on wiring components together:

1. Retrieval is performed by `PortsRetriever` from `rag/retrievers/ports.py` with optional compression, multi-query, and reranking.
2. Results are fed into `prepare_prompt_state`, then transformed into messages via `build_prompt_messages`.
3. The LLM stack is wrapped in `RunnableWithFallbacks`:
   - Primary: structured ChatOpenAI call (JSON contract).
   - Optional backup ChatOpenAI model (when `langchain.chat_openai.backup_model` is set).
   - Fallback: adapter LLM (`OpenAIAdapter`/`OllamaAdapter`).
   - Final fallback: native `QAPipeline` to preserve functionality if LangChain components fail.
4. `_finalize_output` stitches the formatted sections with a Sources list and carries timing telemetry back to the caller.

## Configuration surface

Runtime knobs map to configuration and environment variables:

| Setting | Config key | Env override |
|---------|------------|--------------|
| Multi-query rewrites | `retrieval.use_multiquery` | `LC_USE_MULTIQUERY` |
| Compression filter | `retrieval.use_compression` | `LC_USE_COMPRESSION` |
| Candidate pool size | `retrieval.candidate_multiplier`, `candidate_min`, `candidate_limit`, `candidate_overfetch_factor` | `LC_CANDIDATE_MULTIPLIER`, `LC_CANDIDATE_MIN`, `LC_CANDIDATE_LIMIT`, `LC_CANDIDATE_OVERFETCH_FACTOR` |
| ChatOpenAI enable | `langchain.use_chat_openai` | `LC_USE_CHAT_OPENAI` |
| ChatOpenAI backup | `langchain.chat_openai.backup_model` | `LC_CHAT_BACKUP_MODEL` |

Refer to `configs/runtime/default.yaml` for local defaults and `configs/runtime/openai.yaml` for the hosted preset.

## Regression harness

`invoke regress-langchain` now calls `scripts/retrieval/regress.py`, which outputs per-query metrics and latency deltas. Use it to snapshot changes before shipping new retrieval features.
