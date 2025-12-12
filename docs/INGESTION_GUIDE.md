# Ingestion Redesign: Excel-Driven Metadata & SQLite

## Overview
The goal is to shift from a "scan folder" approach to a "structured ingestion" approach driven by an Excel file. This ensures every document has high-quality metadata (Title, Author, Year, Category) before it even enters the pipeline.

---

## 1. Current Ingestion Flow

### What Happens Now (`scripts/ingest_docling.py`)
1. **Scan**: Looks for all PDFs in `data/raw/*.pdf`
2. **Parse**: Runs Docling on each PDF
3. **Chunk**: Splits text into semantic chunks
4. **Store**: Writes chunks to `data/staging/chunks.jsonl`
5. **Embed**: Generates vectors and builds FAISS index

### Problems
*   **No Metadata**: We only extract filename as title. No year, author, category.
*   **Manual Download**: You have to manually download PDFs to `data/raw`.
*   **No Tracking**: If ingestion fails halfway, we start from scratch.

---

## 2. New Ingestion Flow (Excel-Driven)

### Input: Excel File (`data/metadata/sources.xlsx`)

| doc_id | title | url | year | author | category | description |
|--------|-------|-----|------|--------|----------|-------------|
| report_2024_climate | Climate Report 2024 | https://example.com/climate.pdf | 2024 | IPCC | Environment | Annual report |
| study_ai_ethics | AI Ethics Study | https://arxiv.org/paper.pdf | 2023 | Stanford | Technology | Research paper |

### Step 1: Metadata Loading & PDF Download
**Script**: `scripts/ingest_excel.py`

```python
import pandas as pd
import requests
from pathlib import Path

def download_and_register():
    # 1. Read Excel
    df = pd.read_excel("data/metadata/sources.xlsx")
    
    # 2. For each row
    for idx, row in df.iterrows():
        doc_id = row['doc_id']
        pdf_path = Path(f"data/raw/{doc_id}.pdf")
        
        # 3. Download if needed
        if not pdf_path.exists():
            print(f"Downloading {doc_id}...")
            response = requests.get(row['url'])
            pdf_path.write_bytes(response.content)
        
        # 4. Insert into SQLite
        insert_document(
            doc_id=doc_id,
            title=row['title'],
            filename=f"{doc_id}.pdf",
            source_url=row['url'],
            year=row['year'],
            author=row['author'],
            category=row['category'],
            status='pending'
        )
```

### Step 2: Parse & Chunk (Same as before, but with SQLite)
**Script**: `scripts/ingest_docling.py` (modified)

```python
def process_pending_documents():
    # 1. Query DB for pending documents
    docs = db.query("SELECT * FROM documents WHERE status = 'pending'")
    
    for doc in docs:
        # 2. Parse PDF
        parsed = parse_pdf_multimodal(f"data/raw/{doc['filename']}")
        
        # 3. Chunk
        chunks = chunk_parsed_document(parsed, doc_id=doc['id'])
        
        # 4. Insert chunks into DB
        for chunk in chunks:
            db.insert_chunk(
                id=chunk['id'],
                doc_id=doc['id'],
                text=chunk['text'],
                page=chunk['page'],
                bbox=chunk['bbox']
            )
        
        # 5. Update status
        db.update_document_status(doc['id'], 'processed')
```

### Step 3: Embedding (Same, but reads from SQLite)
**Script**: `scripts/build_embeddings.py` (modified)

```python
def embed_chunks():
    # 1. Get chunks without embeddings
    chunks = db.query("SELECT * FROM chunks WHERE embedding IS NULL")
    
    # 2. Batch embed
    for batch in chunks_batched(chunks):
        embeddings = openai.embed([c['text'] for c in batch])
        
        # 3. Save to DB
        for chunk, emb in zip(batch, embeddings):
            db.update_chunk_embedding(chunk['id'], emb)
```

---

## 3. Database Schema (SQLite)

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,          -- e.g. "report_2024_climate"
    title TEXT NOT NULL,
    filename TEXT NOT NULL,       -- e.g. "report_2024_climate.pdf"
    source_url TEXT,
    year INTEGER,
    author TEXT,
    category TEXT,
    description TEXT,
    page_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' -- pending, processing, processed, failed
);

CREATE TABLE chunks (
    id TEXT PRIMARY KEY,          -- e.g. "report_2024_climate_0001"
    doc_id TEXT NOT NULL,
    chunk_index INTEGER,
    text TEXT NOT NULL,
    page INTEGER,
    bbox TEXT,                    -- JSON "[x, y, w, h]"
    embedding BLOB,               -- Can use sqlite-vss or store as raw bytes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX idx_chunks_page ON chunks(doc_id, page);
```

---

## 4. Benefits of This Approach

### ✅ Structured Metadata
*   You control **exactly** what goes in the system via the Excel file
*   Rich metadata (year, author, category) available for filtering

### ✅ Automatic Download
*   No need to manually download PDFs
*   URLs are tracked in case you need to re-download

### ✅ Resumable Ingestion
*   If the script crashes, the DB tracks which documents are processed
*   Just re-run the script and it continues from where it left off

### ✅ Deep Linking Ready
*   `page` and `bbox` stored in the database
*   Fast lookups: `SELECT * FROM chunks WHERE doc_id = ? AND page = ?`

### ✅ Easy Migration
*   Start with SQLite (zero setup)
*   Later, swap to PostgreSQL with minimal code changes (just change the connection string)

---

## 5. Implementation Plan

### Phase 1: Create SQLite Schema
- [ ] Create `rag/store/db_schema.sql`
- [ ] Create `rag/store/sqlite_store.py` (DB utilities)

### Phase 2: Update Ingestion Scripts
- [ ] Create `scripts/ingest_excel.py` (download + register)
- [ ] Modify `scripts/ingest_docling.py` to write to SQLite
- [ ] Modify `scripts/build_embeddings.py` to read from SQLite

### Phase 3: Update Retrieval
- [ ] Modify `app/services/qa.py` to read from SQLite
- [ ] Test deep linking with new schema

### Phase 4: Migrate Existing Data
- [ ] Script to migrate `chunks.jsonl` → SQLite (if needed)

---

## 6. Next Steps

**To proceed, I need:**
1. A sample of your Excel file (just 2-3 rows) to confirm the schema
2. Your approval to start implementing the SQLite schema

Would you like me to start building this?
