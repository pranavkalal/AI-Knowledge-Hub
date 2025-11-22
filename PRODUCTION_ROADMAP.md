# Production Roadmap: AI Knowledge Hub

This document outlines the steps to transition the AI Knowledge Hub from a local prototype to a production-ready system suitable for real user testing and eventual public deployment.

## Phase 1: Readiness for User Testing (Immediate)
**Goal**: Enable secure, reliable testing with a small group of users and capture their feedback.

### 1. Containerization
- [ ] **Dockerize API**: Create a `Dockerfile` for the FastAPI backend.
- [ ] **Dockerize UI**: Create a `Dockerfile` for the Streamlit frontend.
- [ ] **Docker Compose**: Create a `docker-compose.yml` to spin up both services + a simple vector store (if moving away from local files).

### 2. Basic Security
- [ ] **API Auth**: Implement API Key authentication (or Basic Auth) for the FastAPI endpoints to prevent unauthorized access.
- [ ] **UI Auth**: Add a simple password protection screen to Streamlit (using `st.session_state` or `streamlit-authenticator`) to restrict access during testing.

### 3. Feedback Loop (Critical for Evaluation)
- [ ] **Feedback UI**: Add "Thumbs Up/Down" and "Comment" buttons below each answer in Streamlit.
- [ ] **Feedback Storage**: Log this feedback to a persistent store (e.g., a simple SQLite DB or append to a CSV/JSONL file on disk for now) so you can analyze quality.

### 4. Deployment
- [ ] **Cloud Hosting**: Deploy the Docker containers to a cloud provider (e.g., AWS ECS, Azure Container Apps, or a simple VM like EC2/DigitalOcean).
- [ ] **Persistent Volume**: Ensure the `data/` directory (containing the FAISS index) is mounted as a persistent volume so it survives restarts.

---

## Phase 2: Production Architecture (Medium Term)
**Goal**: Scalability, robustness, and maintainability.

### 1. Data Persistence
- [ ] **Migrate Metadata**: Move from `docs.jsonl` to a relational database (PostgreSQL). This allows for better querying, updates, and data integrity.
- [ ] **Vector Store**: Migrate from local `vectors.faiss` to a managed vector database (e.g., Qdrant, Weaviate, Pinecone) or run a dedicated FAISS server. This handles concurrency and updates better than a file-based index.

### 2. Ingestion Pipeline
- [ ] **Orchestration**: Move ingestion scripts (`rag/ingest_lib`) to a workflow orchestrator (e.g., Airflow, Prefect, Dagster).
- [ ] **Incremental Updates**: Implement logic to only process *new* or *modified* PDFs, rather than rebuilding the entire index every time.

### 3. Advanced Security
- [ ] **OAuth2**: Implement proper user login (Google/Microsoft SSO) for the UI.
- [ ] **RBAC**: Role-Based Access Control (e.g., Admin vs. Viewer).

### 4. Observability
- [ ] **Tracing**: Integrate LangSmith or Arize Phoenix to trace every LLM call, latency, and token usage.
- [ ] **Logging**: Centralized logging (e.g., ELK stack or CloudWatch).

---

## Phase 3: Enterprise Features (Long Term)
**Goal**: High availability and advanced capabilities.

- [ ] **Multi-Tenancy**: Support multiple datasets/knowledge bases.
- [ ] **GraphRAG**: Implement Knowledge Graph extraction for better reasoning across documents.
- [ ] **Hybrid Search**: Fine-tune the hybrid search (Dense + BM25) weights based on user feedback data.
