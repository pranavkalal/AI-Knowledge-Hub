# Requirements

This project targets a Python-first workflow with optional cloud services. Use this as a checklist before building or deploying.

## Runtime baseline

| Item | Recommended | Notes |
|------|-------------|-------|
| OS | macOS 13+, Ubuntu 22.04+, Windows 11 | Any OS with Python 3.10+ and FAISS support |
| Python | 3.10 or 3.11 | Create a virtual environment (`python -m venv .venv`) |
| pip | Latest | `pip install --upgrade pip` before installing deps |
| Git | Recent | Needed for cloning and Invoke tasks |

`requirements.txt` vendors FAISS (CPU), LangChain, Streamlit, FastAPI, Invoke, and the OpenAI SDK. Run `pip install -r requirements.txt` inside your virtualenv.

## Optional tooling

| Capability | Tool | Why |
|------------|------|-----|
| Local LLMs | [Ollama](https://ollama.com/) | Used when `llm.adapter=ollama` for offline inference |
| OCR | Tesseract + `pytesseract`, or AWS Textract/Azure Form Recognizer | Needed for scanned/image-heavy PDFs |
| PDF parsing | `pdfplumber`, `pdfminer.six`, Ghostscript | Improves two-column + table extraction |
| GPU acceleration | CUDA 12.x (optional) | Speeds up embeddings or OCR on heavy corpora |

## Environment variables

Copy `.env.example` → `.env` and fill in:

- `COTTON_RUNTIME` – runtime config (`configs/runtime/openai.yaml` for OpenAI preset).
- `OPENAI_API_KEY` – required when using OpenAI embeddings or reranking.
- `OLLAMA_HOST`, `OLLAMA_MODEL` – if running locally with Ollama.
- `LC_*` overrides – tune retrieval/LLM behaviour at runtime (see README “Everyday commands”).

For production deployments, use a secrets manager or environment injection (Docker secrets, Kubernetes config maps, etc.) instead of raw `.env` files.

## Data storage expectations

```
project/
├─ data/raw/             # downloaded PDFs
├─ data/staging/         # docs.jsonl, cleaned.jsonl, chunks.jsonl
├─ data/embeddings/      # embeddings.npy, ids.npy, vectors.faiss
├─ logs/                 # ingest/build/regression logs
└─ reports/              # regression outputs (optional)
```

Ensure the process has read/write access to these directories. For containerised deployments, mount persistent volumes or S3-compatible buckets.

## Cloud services (optional)

- **OpenAI API** – embeddings, reranker, and ChatOpenAI fallback. Billable per token; set usage caps.
- **Object storage** – S3/GCS/Azure Blob for raw PDFs and fast retrieval.
- **OCR provider** – AWS Textract, Azure Form Recognizer, or Google Document AI if local OCR struggles.

## Verification checklist

- [ ] `python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r requirements.txt`
- [ ] `.env` populated with API keys/runtime path
- [ ] `invoke --list` runs without errors
- [ ] `invoke build` completes and generates `data/embeddings/vectors.faiss`

Once everything passes, move to the [deployment guide](deployment.md) for environment-specific instructions.
