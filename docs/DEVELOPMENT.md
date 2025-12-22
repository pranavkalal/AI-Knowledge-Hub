# Development Guide

## Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+
- **Docker**: For PostgreSQL
- **API Keys**: OpenAI, Azure Document Intelligence

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-org/AI-Knowledge-Hub.git
cd AI-Knowledge-Hub
make install

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start PostgreSQL
make db

# 4. Run dev servers
make dev
# API: http://localhost:8000
# UI: http://localhost:3000
```

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install Python and Node dependencies |
| `make dev` | Run API + Frontend together |
| `make api` | Run FastAPI backend only |
| `make ui` | Run Next.js frontend only |
| `make db` | Start PostgreSQL container |
| `make db-stop` | Stop PostgreSQL |
| `make ingest` | Run PDF ingestion pipeline |
| `make test` | Run pytest suite |
| `make fmt` | Format code with ruff |

---

## Project Structure

```
app/           # FastAPI backend
  routers/     # API endpoints
  adapters/    # Service implementations
  services/    # Business logic
rag/           # RAG core logic
  chain.py     # LangChain orchestration
  ingest_lib/  # Ingestion utilities
frontend/      # Next.js app
  src/app/     # Pages
  src/components/ # UI components
configs/       # YAML configuration
data/raw/      # Source PDFs
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API keys and connection strings |
| `configs/runtime/openai.yaml` | Model and retrieval settings |
| `configs/ingestion/azure_postgres.yaml` | Ingestion parameters |

---

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_pipeline.py -v

# Run with coverage
pytest --cov=app tests/
```

---

## Code Quality

```bash
# Format code
make fmt

# Type checking (optional)
mypy app/
```

---

## Common Tasks

### Add a new API endpoint
1. Create router in `app/routers/`
2. Register in `app/main.py`
3. Add schema in `app/schemas.py`

### Modify retrieval behavior
1. Edit `rag/chain.py` for pipeline changes
2. Edit `app/adapters/vector_postgres.py` for search changes
3. Update `configs/runtime/openai.yaml` for parameters

### Update prompts
1. Edit `app/services/prompting.py`
2. Modify persona templates as needed

### Re-embed with new model
```bash
PYTHONPATH=. python scripts/reembed_chunks.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" on port 5432 | Run `make db` to start PostgreSQL |
| "Invalid API key" | Check `.env` file |
| Frontend 404 on API calls | Ensure API is running on port 8000 |
| Embedding dimension mismatch | Re-embed chunks after model change |
