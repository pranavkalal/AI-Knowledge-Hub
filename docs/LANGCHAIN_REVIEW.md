# LangChain Implementation Review

## Overview
The LangChain implementation in `rag/chain.py` orchestrates the RAG pipeline using **LCEL (LangChain Expression Language)**. It wraps the native `QAPipeline` components (retriever, reranker, LLM) into a graph of Runnables.

## Current Architecture

### 1. Composition (LCEL)
The chain is composed using the pipe `|` syntax:
```python
chain = (
    RunnableLambda(_init_timeline)
    | { ...inputs... }
    | RunnableLambda(prepare_prompt_state)
    | { "llm": llm_runnable, ... }
    | RunnableLambda(_finalize_output)
)
```
This structure is modern and allows for easy inspection and modification of intermediate steps.

### 2. Retrieval (`_RetrievalRunnable`)
- Wraps the native `PortsRetriever`.
- Handles **Reranking** explicitly within the runnable.
- Supports **MultiQuery** (generating multiple search queries) and **Contextual Compression** (filtering irrelevant context).
- **Timing**: It captures detailed timing metrics (ANN search, stitching, reranking) which is excellent for performance profiling.

### 3. LLM & Fallbacks
- Uses `RunnableWithFallbacks` to provide high availability.
- **Primary**: `_structured_chat_runnable` (ChatOpenAI) which parses JSON output.
- **Fallbacks**:
    1. Backup ChatOpenAI model.
    2. Plain text ChatOpenAI (if JSON parsing fails).
    3. Native Adapter (non-LangChain fallback).
    4. Native Pipeline (complete bypass).

### 4. Structured Output
- Currently uses manual JSON parsing:
  ```python
  payload = json.loads(raw_text)
  structured = StructuredAnswer(**payload)
  ```
- This relies on the LLM following the system prompt's JSON instructions.

### 5. Routing (`rag/router_chain.py`)
- Uses a simple **keyword-based** router (`route_by_question_type`).
- Routes to: `definition`, `statistic`, or `impact` (default).
- This is a lightweight prototype but brittle for complex queries.

---

## Suggestions for Improvement

### 1. Robust Structured Output
**Current**: Manual `json.loads`.
**Problem**: Prone to syntax errors if the LLM hallucinates markdown blocks or malformed JSON.
**Fix**: Use OpenAI's native function calling or JSON mode via `with_structured_output`.
```python
# New approach
structured_llm = chat_llm.with_structured_output(StructuredAnswer)
```
This guarantees valid JSON matching the Pydantic schema.

### 2. Semantic Routing
**Current**: Keyword matching ("what is", "statistic").
**Problem**: Fails on "Tell me about the numbers regarding water usage" (might miss "statistic" keyword).
**Fix**: Use a **Semantic Router** (embedding-based) or an LLM-based router.
```python
from langchain.chains.router import MultiPromptChain
# Or use a lightweight classifier
router_chain = (
    PromptTemplate.from_template("Classify this question: {question}")
    | chat_llm
    | StrOutputParser()
    | route_dispatch
)
```

### 3. Chat History (Memory)
**Current**: Single-turn QA.
**Problem**: Cannot handle follow-up questions ("What about 2022?").
**Fix**: Add `RunnableWithMessageHistory` or manually inject `chat_history` into the prompt.
```python
chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="chat_history",
)
```

### 4. True Async Support
**Current**: `_native_pipeline_runnable` calls `pipeline.ask` which is synchronous. `ainvoke` wraps it in `asyncio.to_thread`.
**Problem**: Blocks a thread during I/O (DB/Network), limiting concurrency under load.
**Fix**: Refactor `QAPipeline.ask` and `sqlite_store` to support `async` methods natively (e.g., using `aiosqlite`).

### 5. Observability
**Current**: Custom `LoggingCallbackHandler` and `_TIMELINE` context var.
**Fix**: Integrate **LangSmith**. It provides superior tracing, debugging, and dataset management out of the box with just environment variables.

### 6. Dynamic Configuration
**Current**: Configuration is passed at build time.
**Fix**: Use `configurable_fields` to allow changing parameters (like `k`, `temperature`) at runtime per-request without rebuilding the chain.
```python
retriever.configurable_fields(
    top_k=ConfigurableField(id="k")
)
```
