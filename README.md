# AI-Knowledge-Hub

A web-based GenAI portal for CRDC to summarize and track R&D investments across structured and unstructured data.

---

## Data Ingestion

We use an ingestion pipeline to collect cotton research PDFs, extract text/metadata, and run quality checks.

### Quickstart
Run these 2. Refer MakeFile

make ingest

make eval.extract

What happens
Discover PDFs from configs/ingestion.yaml
Download into data/raw/
Parse text + metadata into:
data/staging/docs.jsonl (full records)
data/staging/docs.csv (index view)
Run QA checks → reports/extraction_audit.csv
Skip broken/irrelevant docs listed in eval/skip_ids.txt

Make Targets
make ingest → run ingestion
make eval.extract → run QA check and write audit report
