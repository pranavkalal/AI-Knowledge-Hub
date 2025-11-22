#!/usr/bin/env python3
"""
Low-impact batch ingestion script using Docling.
Processes PDFs slowly with delays to avoid overwhelming the machine.
"""

import sys
import os
import logging
import json
import subprocess
import time
import gc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rag.ingest_lib.parse_docling import parse_pdf_multimodal, elements_to_records
from rag.segment.semantic_chunker import chunk_record_semantic
from rag.store.sqlite_store import (
    get_documents_by_status, 
    insert_chunks, 
    update_document_status,
    get_all_chunks
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd):
    logger.info(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def ingest_low_impact():
    """Process PDFs with low CPU/memory impact."""
    chunks_path = Path("data/staging/chunks.jsonl")
    
    docs = get_documents_by_status('downloaded')
    
    if not docs:
        logger.warning("No 'downloaded' documents found in SQLite.")
        return

    logger.info(f"Found {len(docs)} documents to process (LOW IMPACT MODE)")
    logger.info("⚡ Running with: delayed processing, aggressive GC, lower priority")
    
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    
    new_chunks_count = 0

    for idx, doc in enumerate(docs, 1):
        pdf_path = Path("data/raw") / doc['filename']
        
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            continue

        try:
            logger.info(f"[{idx}/{len(docs)}] Processing {doc['title'][:60]}...")
            
            # Parse with Docling
            parsed = parse_pdf_multimodal(str(pdf_path))
            
            # Convert to records
            records = elements_to_records(
                parsed, 
                doc['id'], 
                extra_meta={
                    "title": doc['title'],
                    "filename": doc['filename']
                }
            )
            logger.info(f"  Extracted {len(records)} elements")
            
            # Aggressive cleanup
            del parsed
            gc.collect()

            # Chunk (Semantic)
            doc_chunks = []
            for rec in records:
                chunks = chunk_record_semantic(rec)
                doc_chunks.extend(chunks)
            
            logger.info(f"  Generated {len(doc_chunks)} chunks")
            
            # Write to SQLite
            if doc_chunks:
                insert_chunks(doc_chunks)
                update_document_status(doc['id'], 'processed')
                new_chunks_count += len(doc_chunks)
            
            # Cleanup
            del records
            del doc_chunks
            gc.collect()
            
            # 🐌 DELAY: Give the machine a breather (3 seconds between docs)
            if idx < len(docs):
                logger.info("  💤 Pausing 3s to reduce load...")
                time.sleep(3)
                
        except Exception as e:
            logger.error(f"Failed to process {doc['filename']}: {e}")
            import traceback
            traceback.print_exc()

    if new_chunks_count == 0:
        logger.warning("No new chunks generated.")
        return
    
    # Export to JSONL
    logger.info("Exporting all chunks from SQLite to JSONL...")
    all_db_chunks = get_all_chunks()
    
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_db_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Build embeddings & FAISS
    logger.info("Building embeddings (this may take a while with API rate limits)...")
    emb_eds = "data/embeddings/embeddings.npy"
    emb_ids = "data/embeddings/ids.npy"
    faiss_idx = "data/embeddings/vectors.faiss"
    
    Path(emb_eds).parent.mkdir(parents=True, exist_ok=True)
    python_exe = sys.executable
    
    # Smaller batch size = less memory, more API calls (slower but gentler)
    run_command(f"{python_exe} -m scripts.build_embeddings --chunks {chunks_path} --out_vecs {emb_eds} --out_ids {emb_ids} --model text-embedding-3-small --adapter openai --batch 128 --normalize")
    
    logger.info("Building FAISS index...")
    run_command(f"{python_exe} -m scripts.build_faiss --vecs {emb_eds} --index_out {faiss_idx}")

    logger.info(f"\n✅ Ingestion Complete! Indexed {len(all_db_chunks)} chunks.")

if __name__ == "__main__":
    ingest_low_impact()
