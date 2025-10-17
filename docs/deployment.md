# Deployment guide

This guide covers running the Knowledge Hub in dev, staging, or production environments.

## 1. Configuration snapshot

- **Runtime config** – `COTTON_RUNTIME` points to `configs/runtime/openai.yaml` (OpenAI preset) or `configs/runtime/default.yaml` for local experiments.
- **Environment variables** – load from `.env`, container secrets, or your CI/CD pipeline. Key settings: `OPENAI_API_KEY`, `OLLAMA_*`, `LC_*` flags, `HOST`/`PORT`.
- **Data paths** – ensure writable volumes for `data/raw`, `data/staging`, `data/embeddings`, and `logs`.

## 2. Development server (local)

```bash
invoke build    # optional: first-time corpus build
invoke dev      # runs FastAPI + Streamlit together
```

FastAPI serves under `http://localhost:8000`, Streamlit at `http://localhost:8501`. Logs appear in the console and `logs/` (if configured).

## 3. API-only deployment

### Using Uvicorn/Gunicorn

```bash
pip install -r requirements.txt
invoke embed && invoke faiss   # make sure vectors.faiss exists
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For production, place Uvicorn behind an HTTPS reverse proxy (Nginx, Traefik) and enable process supervision (systemd, supervisor, or a container orchestrator).

### Docker (sample)

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV COTTON_RUNTIME=configs/runtime/openai.yaml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Mount volumes or bake artefacts (`vectors.faiss`, `embeddings.npy`, etc.) into the image as needed. Inject secrets via environment variables or Docker secrets.

## 4. Streamlit UI deployment

- Low-friction: run `streamlit run ui/streamlit_app.py --server.port 8501` alongside the API.
- Production: host behind a reverse proxy, configure session secrets if enabling auth.

## 5. CI/CD pointers

1. **Install dependencies** – `pip install -r requirements.txt`.
2. **Lint/tests** – run `python -m pytest tests/langchain` and custom checks (optional linting tasks).
3. **Regressions** – execute `invoke regress-langchain --after configs/runtime/openai.yaml --out reports/regression.json` with a stable baseline to detect retrieval drift.
4. **Build artefacts** – trigger ingestion/build only when upstream PDFs change (consider caching `data/embeddings` between builds).

## 6. Observability & telemetry

- **Logs** – FastAPI logs to stdout; LangChain telemetry prints `[lc.qa]` and `[lc.debug]` lines.
- **Metrics** – optional: pipe logs into ELK/CloudWatch or use Honeycomb’s LangChain integration.
- **Regression reports** – store `reports/regression.json` artifacts for trend analysis.

## 7. Scaling considerations

- **Embedder/RAG** – CPU is fine for small corpora; GPU embeddings (OpenAI, BGE, or local) accelerate large updates.
- **OCR** – external services (Textract/Form Recognizer) scale better than on-prem Tesseract for heavy scans.
- **Vector store** – FAISS sits on local disk; for multi-node deployments consider migrating to managed vector DBs (Pinecone, Qdrant Cloud) with similar retrieval semantics.

## 8. Security checklist

- [ ] Store API keys in a secrets manager, not in repo or logs.
- [ ] Restrict network egress if running inside a VPC.
- [ ] Add authentication/authorization to FastAPI endpoints before exposing publicly.
- [ ] Keep dependency lockfile (requirements.txt) up to date with security patches.

Deployment-ready? Move on to ingestion specifics (`docs/ingestion.md`) or orchestration internals (`docs/orchestration.md`) depending on your role.
