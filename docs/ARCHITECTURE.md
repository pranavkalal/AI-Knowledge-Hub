# System Architecture Deep Dive

## Introduction

This document outlines the architectural decisions behind the CRDC AI Knowledge Hub. It serves as a technical reference for understanding how we solved the challenge of querying 40+ years of unstructured PDF research reports.

## 1. The Challenge (Unstructured Data)

Agricultural research reports are complex:
- **Multi-column layouts**: Hard for standard parsers to read correctly.
- **Embedded Tables**: Critical data is often trapped in grids that look like text soup to simple OCR.
- **Domain Specificity**: "Bt cotton" and "Verticillium wilt" need semantic understanding, not just keyword matching.

## 2. The Solution: Corrective RAG (CRAG) with LangGraph

We moved beyond simple "Retrieve-and-Generate" to an **Agentic** approach.

### 2.1 The Graph Flow

The system operates as a state machine (built with LangGraph):

1.  **Retrieval**: We fetch documents using a hybrid approach (Dense Vectors + BM25 Keywords).
2.  **Grading (Self-Correction)**: A lightweight LLM "Grader" evaluates each retrieved document.
    - *Is this relevant to the question?*
    - If **Yes**: Keep it.
    - If **No**: Discard it.
    - If **Too few docs**: Trigger "Query Transformation" to rewrite the search and try again.
3.  **Generation**: The final context is passed to GPT-4o.
4.  **Hallucination Check**: The generated answer is cross-checked against the documents. If it cites facts not present, we regenerate.

### 2.2 The Ingestion Pipeline

Data quality is paramount. Our pipeline uses **Azure Document Intelligence** (Layout Model) to:
- Detect table boundaries.
- Extract headers and footers (avoiding ingestion of page numbers).
- Chunk text by *semantic sections* rather than arbitrary character counts.

## 3. Infrastructure & Scalability

- **Containerization**: Docker-based build for consistency.
- **Serverless**: Deployed on Google Cloud Run for auto-scaling to zero to save costs.
- **Vector Store**: PostgreSQL with `pgvector` was chosen over Pinecone/Weaviate for simplified stack management (keeping relational metadata and vectors in one place).

## 4. Why This Stack?

| Component | Choice | Reasoning |
| :--- | :--- | :--- |
| **LLM** | OpenAI GPT-4o | Best-in-class reasoning for complex scientific queries. |
| **Framework** | FastAPI | High-performance async support for concurrent RAG requests. |
| **Orchestration** | LangChain/LangGraph | Provides the control flow primitives needed for cyclic graphs. |
| **Frontend** | Next.js | Server-Side Rendering (SSR) for fast initial load and SEO. |

---

*This architecture represents a modern, production-grade approach to Enterprise Search.*
