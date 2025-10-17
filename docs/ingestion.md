# Ingestion pipeline

Everything starts with the crawl → parse → normalize loop. This document explains how to configure and operate ingestion.

## Config file

`configs/ingestion/default.yaml` drives the process. Key keys:

| Key | Description |
|-----|-------------|
| `run_name` | Used for log labels or analytics |
| `years` | Filters seed URLs by publication year |
| `seed_urls` | InsideCotton search/category pages to crawl |
| `include_patterns` | Regex allowlist (e.g. `\.pdf`) |
| `exclude_patterns` | Regex blocklist (`newsletter`, `poster`, etc.) |
| `retry.attempts` / `retry.backoff_secs` | Download retry policy |
| `timeout_secs` | HTTP timeout per request |
| `download_dir` | Where PDFs are stored under `data/raw/` |
| `paths.raw_jsonl` / `cleaned_jsonl` | Optional intermediate files |
| `output.jsonl` / `output.csv` | Primary document outputs |

Override the config per run: `invoke ingest --config configs/ingestion/custom.yaml`.

## Workflow steps

1. **Discover** – `collect_pdf_links` walks each seed URL, applying include/exclude patterns and deduplicating results.
2. **Skip list** – `eval/skip_ids.txt` suppresses known bad or sensitive documents.
3. **Download** – `download_pdf` streams PDFs into `data/raw`. Retries and backoff are configurable.
4. **Parse** – `parse_pdf` extracts text + metadata (title, year, page count). Future work: OCR fallback and column-aware extraction.
5. **Persist** – `write_jsonl` and `write_csv` emit records to `data/staging/docs.*` with metadata fields used downstream (page numbers, source URL, relative paths).

## Tips for image/table-heavy reports

- Use OCR: install `pytesseract` and add an OCR pass inside `parse_pdf` for scanned PDFs. For higher accuracy, integrate AWS Textract/Azure Form Recognizer.
- Two-column PDFs benefit from layout-aware parsers (`pdfplumber`, `pdfminer.six` with `LAParams`).
- Capture extra metadata (`column`, `bbox`, `ocr_confidence`) so the RAG layer can include better snippets and future highlighting.

## Running ingestion

```bash
invoke ingest                         # default config
invoke ingest --config path/to.yaml   # custom crawl
```

After a successful run, expect:

```
data/raw/*.pdf
data/staging/docs.jsonl
data/staging/docs.csv
```

Follow up with:

```bash
invoke chunk    # optional cleaning + chunking
invoke embed
invoke faiss
```

## Error handling

- Failures are logged to stdout and `logs/` when using `invoke`. Add structured logging (JSON) if you need richer observability.
- Append problematic doc IDs to `eval/skip_ids.txt` to skip them on future runs.
- Consider creating `logs/ingest_failures.jsonl` for long-term analysis (URL, reason, timestamp).

## Custom crawls

- Add or remove seed URLs to target specific series or years.
- Use include/exclude regex to target only “Final Report” documents or to avoid newsletters.
- When running one-off ingest jobs (e.g., new dataset drop), store the output under `data/staging/docs_<suffix>.jsonl` and merge during chunking.

For more detail on how ingestion feeds the RAG chain, see `docs/architecture.md` and the orchestration notes in `docs/orchestration.md`.
