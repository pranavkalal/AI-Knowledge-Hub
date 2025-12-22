#!/usr/bin/env python3
"""
Re-embed existing chunks with a new embedding model.
This script:
1. Reads all existing chunks from PostgreSQL
2. Re-embeds them with text-embedding-3-large (3072 dims)
3. Updates the embeddings in-place (recreates table with new vector size)

Usage:
    python scripts/reembed_chunks.py

Cost estimate: ~$0.05 for 1000 chunks
"""

import os
import json
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Configuration
OLD_DIM = 1536
NEW_DIM = 3072
NEW_MODEL = "text-embedding-3-large"
TABLE_NAME = "chunks"
BATCH_SIZE = 100


def main():
    # --- Setup ---
    connection_string = os.environ.get("POSTGRES_CONNECTION_STRING")
    if not connection_string:
        print("❌ Missing POSTGRES_CONNECTION_STRING")
        sys.exit(1)
    
    engine = create_engine(connection_string)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # --- Load embedder ---
    print(f"🔧 Loading embedder: {NEW_MODEL}")
    from app.adapters.loader import load_embedder
    embed_cfg = {"provider": "openai", "model": NEW_MODEL}
    embedder = load_embedder(embed_cfg, os.environ)
    
    # --- Check current table ---
    result = session.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
    total_chunks = result.scalar()
    print(f"📊 Found {total_chunks} chunks to re-embed")
    
    if total_chunks == 0:
        print("Nothing to re-embed. Exiting.")
        return
    
    # --- Read all chunks ---
    print("📖 Reading existing chunks...")
    result = session.execute(text(f"""
        SELECT id, doc_id, chunk_index, page_number, text, metadata
        FROM {TABLE_NAME}
        ORDER BY id
    """))
    
    chunks = []
    for row in result:
        chunks.append({
            "id": row.id,
            "doc_id": row.doc_id,
            "chunk_index": row.chunk_index,
            "page_number": row.page_number,
            "text": row.text,
            "metadata": row.metadata
        })
    
    print(f"   Loaded {len(chunks)} chunks")
    
    # --- Backup: rename old table ---
    print("💾 Backing up old table...")
    session.execute(text(f"ALTER TABLE IF EXISTS {TABLE_NAME} RENAME TO {TABLE_NAME}_backup_1536"))
    session.commit()
    
    # --- Create new table with 3072 dims ---
    print(f"🔨 Creating new table with {NEW_DIM} dimensions...")
    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    session.execute(text(f"""
        CREATE TABLE {TABLE_NAME} (
            id TEXT PRIMARY KEY,
            doc_id TEXT,
            chunk_index INTEGER,
            page_number INTEGER,
            text TEXT,
            embedding vector({NEW_DIM}),
            metadata JSONB,
            search_vector tsvector,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes
    session.execute(text(f"""
        CREATE INDEX IF NOT EXISTS {TABLE_NAME}_embedding_idx 
        ON {TABLE_NAME} USING hnsw (embedding vector_cosine_ops)
    """))
    session.execute(text(f"""
        CREATE INDEX IF NOT EXISTS {TABLE_NAME}_search_vector_idx 
        ON {TABLE_NAME} USING gin (search_vector)
    """))
    session.commit()
    print("   ✅ New table created")
    
    # --- Re-embed in batches ---
    print(f"🚀 Re-embedding {len(chunks)} chunks in batches of {BATCH_SIZE}...")
    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        texts = [c["text"] for c in batch]
        
        # Embed
        embeddings = embedder.embed_texts(texts)
        
        # Insert
        for chunk, emb in zip(batch, embeddings):
            meta_json = json.dumps(chunk["metadata"]) if isinstance(chunk["metadata"], dict) else chunk["metadata"]
            
            session.execute(text(f"""
                INSERT INTO {TABLE_NAME} (id, doc_id, chunk_index, page_number, text, embedding, metadata, search_vector)
                VALUES (:id, :doc_id, :chunk_index, :page_number, :text, :embedding, :metadata, to_tsvector('english', :text))
            """), {
                "id": chunk["id"],
                "doc_id": chunk["doc_id"],
                "chunk_index": chunk["chunk_index"],
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "embedding": str(emb),
                "metadata": meta_json
            })
        
        session.commit()
        print(f"   ✅ Batch {i//BATCH_SIZE + 1}/{(len(chunks) + BATCH_SIZE - 1)//BATCH_SIZE}: {len(batch)} chunks")
    
    # --- Verify ---
    result = session.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
    new_count = result.scalar()
    
    print(f"\n✨ Re-embedding complete!")
    print(f"   Old table: {TABLE_NAME}_backup_1536 ({total_chunks} chunks, 1536 dims)")
    print(f"   New table: {TABLE_NAME} ({new_count} chunks, {NEW_DIM} dims)")
    print(f"\n💡 To clean up, run: DROP TABLE {TABLE_NAME}_backup_1536;")
    
    session.close()


if __name__ == "__main__":
    main()
