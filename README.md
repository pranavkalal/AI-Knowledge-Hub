# AI-Knowledge-Hub

A web-based GenAI portal for CRDC to summarize and track R&D investments across structured and unstructured data.

---

## 📥 Data Ingestion

We use an ingestion pipeline to collect cotton research PDFs, extract text/metadata, and run quality checks.

### Quickstart
```bash
make ingest

make eval.extract
```


## Chunking & Sanity Checks
Split cleaned text into manageable chunks and run basic stats. Run these two commands OR refer Makefile. 

```bash
python app/chunk.py --in data/staging/docs.jsonl --out data/staging/chunks.jsonl --max_tokens 512 --overlap 64

python scripts_sanity/chunk_stats.py --in data/staging/chunks.jsonl

```

This prints:
number of docs and total chunks
avg/min/max tokens per chunk (with P50 and P90)
avg/min/max chars per chunk
sample chunk preview