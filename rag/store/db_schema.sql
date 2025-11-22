-- SQLite schema for AI Knowledge Hub
-- Supports rich metadata from CRDC Excel file and deep linking

-- Core document metadata
CREATE TABLE IF NOT EXISTS documents (
    -- Primary identifier from Excel
    id TEXT PRIMARY KEY,              -- uuid from Excel
    
    -- Core fields
    title TEXT NOT NULL,
    filename TEXT,                    -- Generated as "{id}.pdf"
    source_url TEXT NOT NULL,         -- field_files (PDF URL)
    
    -- Searchable metadata
    year INTEGER,                     -- Extracted from field_date_issued
    authors TEXT,                     -- field_author
    categories TEXT,                  -- field_subject (comma-separated)
    description TEXT,                 -- field_abstract
    publisher TEXT,                   -- field_publisher
    document_type TEXT,               -- type (Article, Research, etc.)
    
    -- Additional identifiers
    uid TEXT,                         -- uid from Excel
    alternative_title TEXT,           -- field_alternative_title
    
    -- Flexible storage for remaining fields
    metadata TEXT,                    -- JSON: field_collections, field_copyright, field_identifier, etc.
    
    -- Tracking fields
    page_count INTEGER,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'    -- pending, downloading, parsing, processed, failed
);

-- Text chunks for retrieval
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,              -- e.g. "uuid_0042"
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Content
    text TEXT NOT NULL,
    
    -- Deep linking
    page INTEGER,
    bbox TEXT,                        -- JSON "[x, y, w, h]"
    
    -- Embeddings (optional: can use FAISS separately)
    embedding BLOB,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_page ON chunks(doc_id, page);
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_authors ON documents(authors);
CREATE INDEX IF NOT EXISTS idx_documents_categories ON documents(categories);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
