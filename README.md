# AI-Knowledge-Hub

A web-based GenAI portal for CRDC to summarize and track R&D investments across structured and unstructured data.

---

## 📥 Data Ingestion

We use an ingestion pipeline to collect cotton research PDFs, extract text/metadata, and run quality checks.

### Quickstart
```bash
make ingest
make eval.extract
