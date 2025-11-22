#!/usr/bin/env python3
"""
Batch ingestion script using Docling.
Scans data/raw for PDFs, parses them, chunks them, and rebuilds the index.
"""

import sys
import os
import logging
import json
import subprocess
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.ingest_lib.parse_docling import parse_pdf_multimodal, elements_to_records
from rag.segment.semantic_chunker import chunk_record_semantic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd):
    logger.info(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

from rag.store.sqlite_store import (
    get_documents_by_status, 
    insert_chunks, 
    update_document_status,
    get_all_chunks
)

def ingest_data_raw():
    chunks_path = Path("data/staging/chunks.jsonl")
    
    # 1. Fetch documents from SQLite
    docs = get_documents_by_status('downloaded')
    
    if not docs:
        logger.warning("No 'downloaded' documents found in SQLite.")
        return

    logger.info(f"Found {len(docs)} documents to process in SQLite")
    
    # Ensure staging dir exists
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    
    new_chunks_count = 0

    # Process PDFs one by one
    import gc
    
    for doc in docs:
        pdf_path = Path("data/raw") / doc['filename']
        
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            continue

        try:
            logger.info(f"Processing {doc['title']} ({doc['filename']})...")
            
            # 1. Parse with Docling
            parsed = parse_pdf_multimodal(str(pdf_path))
            
            # 2. Convert to records
            records = elements_to_records(
                parsed, 
                doc['id'], 
                extra_meta={
                    "title": doc['title'],
                    "filename": doc['filename']
                }
            )
            logger.info(f"  Extracted {len(records)} elements")
            
            # Clear parsed object
            del parsed
            gc.collect()

            # 3. Chunk (Semantic)
            doc_chunks = []
            for rec in records:
                chunks = chunk_record_semantic(rec)
                doc_chunks.extend(chunks)
            
            logger.info(f"  Generated {len(doc_chunks)} chunks")
            
            # 4. Write to SQLite
            if doc_chunks:
                insert_chunks(doc_chunks)
                update_document_status(doc['id'], 'processed')
                new_chunks_count += len(doc_chunks)
            
            # Clear records
            del records
            del doc_chunks
            gc.collect()
                
        except Exception as e:
            logger.error(f"Failed to process {doc['filename']}: {e}")
            import traceback
            traceback.print_exc()

    if new_chunks_count == 0:
        logger.warning("No new chunks generated.")
    
    # 5. Export ALL chunks from SQLite to JSONL for embedding script
    logger.info("Exporting all chunks from SQLite to JSONL for embedding generation...")
    all_db_chunks = get_all_chunks()
    
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_db_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # 6. Run Embedding and FAISS build
    logger.info("Building embeddings...")
    emb_eds = "data/embeddings/embeddings.npy"
    emb_ids = "data/embeddings/ids.npy"
    faiss_idx = "data/embeddings/vectors.faiss"
    
    Path(emb_eds).parent.mkdir(parents=True, exist_ok=True)

    # Use the SAME python executable that is running this script
    python_exe = sys.executable
    
    run_command(f"{python_exe} -m scripts.build_embeddings --chunks {chunks_path} --out_vecs {emb_eds} --out_ids {emb_ids} --model text-embedding-3-small --adapter openai --batch 256 --normalize")
    
    logger.info("Building FAISS index...")
    run_command(f"{python_exe} -m scripts.build_faiss --vecs {emb_eds} --index_out {faiss_idx}")

    logger.info(f"\n✅ Ingestion Complete! Indexed {len(all_db_chunks)} chunks.")

if __name__ == "__main__":
    ingest_data_raw()
