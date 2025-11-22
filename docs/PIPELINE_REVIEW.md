# RAG Pipeline Review & High-Level Design

## Current Architecture

The current system uses a **file-based** architecture, which is simple to start with but has significant limitations for scaling and complex features like deep linking.

### Data Flow
1.  **Ingestion (`scripts/ingest_docling.py`)**
    *   **Input**: PDFs in `data/raw`.
    *   **Parsing**: `Docling` parses PDFs into structured elements (text, tables).
    *   **Chunking**: Text is split into chunks (Semantic/Fixed-size).
    *   **Storage**: All chunks are written to a single **JSONL file** (`data/staging/chunks.jsonl`).
    *   **Embeddings**: `scripts.build_embeddings` reads the JSONL, generates embeddings via OpenAI, and saves them as a **Numpy array** (`data/embeddings/embeddings.npy`).
    *   **Indexing**: `scripts.build_faiss` builds a FAISS index (`data/embeddings/vectors.faiss`) from the numpy array.

2.  **Retrieval (`app/services/qa.py`)**
    *   **Query**: User asks a question.
    *   **Search**: Query is embedded and searched against the FAISS index.
    *   **Lookup**: The system maps FAISS indices back to the **JSONL file** to retrieve the actual text and metadata. This often requires loading large files into memory or inefficient line-seeking.
    *   **Generation**: Retrieved text is passed to the LLM to generate an answer.

### Limitations (Why "JSON is not ideal")
*   **Performance**: Reading from a massive JSONL file for every query is slow and memory-intensive.
*   **Data Integrity**: No schema enforcement. Metadata can be inconsistent.
*   **Deep Linking**: Difficult to efficiently query for specific pages or bounding boxes without scanning the whole file.
*   **Scalability**: Hard to manage thousands of documents.

---

## Proposed High-Level Design (Multi-Modal RAG)

To support **Multi-Modal RAG** (Text + Images + Tables) and **Deep Linking** (jumping to specific text on a PDF page), we need a relational database.

### 1. Database Schema (SQLite / PostgreSQL)

We will replace `chunks.jsonl` with a structured database. **SQLite** is recommended for local development (zero-setup), while **PostgreSQL** is best for production.

#### Tables

**`documents`**
*   `id` (PK): Unique Document ID (e.g., `docling_test_001`)
*   `filename`: Original filename
*   `title`: Document title
*   `page_count`: Total pages
*   `ingested_at`: Timestamp
*   `metadata`: JSON blob for extra fields (year, author, url)

**`chunks`**
*   `id` (PK): Unique Chunk ID (e.g., `docling_test_001_chunk005`)
*   `doc_id` (FK): Reference to `documents.id`
*   `chunk_index`: Order in the document
*   `text`: The actual text content
*   `page`: Page number (Critical for Deep Linking)
*   `bbox`: JSON `[x, y, w, h]` (Critical for highlighting text on the PDF)
*   `embedding_id`: Reference to the vector store index (optional, if using external FAISS)

### 2. Updated Pipeline

#### Ingestion
1.  **Parse**: Docling extracts text, **page numbers**, and **bounding boxes**.
2.  **Store**: 
    *   Insert document info into `documents` table.
    *   Insert chunks with `text`, `page`, and `bbox` into `chunks` table.
3.  **Embed**: Generate embeddings for chunks.
4.  **Index**: 
    *   **Option A (Simple)**: Store embeddings in FAISS (as now), but map FAISS ID -> Database Primary Key.
    *   **Option B (Robust)**: Use `pgvector` (PostgreSQL) or `sqlite-vss` to store embeddings directly in the DB.

#### Retrieval & Deep Linking
1.  **Search**: Query vector store to get top Chunk IDs.
2.  **Fetch**: `SELECT * FROM chunks WHERE id IN (...)`. This is instant.
3.  **Deep Link**: The returned `Citation` object now contains:
    *   `doc_id`: To load the PDF.
    *   `page`: To scroll to the right page.
    *   `bbox`: To draw a highlight box around the text.

### 3. Multi-Modal Enhancements
*   **Images**: Store extracted images from PDFs in a `assets/images` folder and reference their paths in a new `images` table (linked to `doc_id` and `page`).
*   **Tables**: Store parsed table HTML/Markdown in a `tables` table or as a special chunk type.

## Recommendation
**Migrate to SQLite** immediately. It requires no extra infrastructure (it's just a file), supports SQL queries, and solves the "JSON text storage" issue. It natively supports the structured metadata needed for robust deep linking.
