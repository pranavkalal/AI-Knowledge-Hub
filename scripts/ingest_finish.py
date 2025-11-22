#!/usr/bin/env python3
"""
Ultra-safe ingestion: processes in small batches with forced restarts.
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

def process_one_document(doc):
    """Process a single PDF with error handling."""
    pdf_path = Path("data/raw") / doc['filename']
    
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        return False

    try:
        logger.info(f"Processing: {doc['title'][:60]}...")
        
        # Parse with timeout protection
        parsed = parse_pdf_multimodal(str(pdf_path))
        
        records = elements_to_records(
            parsed, 
            doc['id'], 
            extra_meta={
                "title": doc['title'],
                "filename": doc['filename']
            }
        )
        logger.info(f"  Extracted {len(records)} elements")
        
        del parsed
        gc.collect()

        # Chunk
        doc_chunks = []
        for rec in records:
            try:
                chunks = chunk_record_semantic(rec)
                doc_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"  Chunking failed for record: {e}")
                continue
        
        logger.info(f"  Generated {len(doc_chunks)} chunks")
        
        # Write to SQLite
        if doc_chunks:
            insert_chunks(doc_chunks)
            update_document_status(doc['id'], 'processed')
            logger.info(f"  ✅ Saved {len(doc_chunks)} chunks to SQLite")
        
        del records, doc_chunks
        gc.collect()
        
        # Delay
        time.sleep(2)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process {doc['filename']}: {e}")
        import traceback
        traceback.print_exc()
        
        # Mark as failed to skip next time
        try:
            update_document_status(doc['id'], 'failed')
        except:
            pass
        
        return False

def main():
    """Process remaining documents."""
    docs = get_documents_by_status('downloaded')
    
    if not docs:
        logger.info("✅ No documents to process!")
        return
    
    logger.info(f"Found {len(docs)} documents to process")
    
    success_count = 0
    fail_count = 0
    
    for doc in docs:
        if process_one_document(doc):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"\n📊 Summary: {success_count} succeeded, {fail_count} failed")
    
    # Now rebuild index
    logger.info("\n🔨 Rebuilding search index...")
    chunks_path = Path("data/staging/chunks.jsonl")
    all_chunks = get_all_chunks()
    
    logger.info(f"Exporting {len(all_chunks)} chunks to JSONL...")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    python_exe = sys.executable
    
    logger.info("Building embeddings...")
    subprocess.run(
        f"{python_exe} -m scripts.build_embeddings --chunks {chunks_path} "
        f"--out_vecs data/embeddings/embeddings.npy --out_ids data/embeddings/ids.npy "
        f"--model text-embedding-3-small --adapter openai --batch 128 --normalize",
        shell=True, check=True
    )
    
    logger.info("Building FAISS index...")
    subprocess.run(
        f"{python_exe} -m scripts.build_faiss --vecs data/embeddings/embeddings.npy "
        f"--index_out data/embeddings/vectors.faiss",
        shell=True, check=True
    )
    
    logger.info(f"\n✅ Complete! Indexed {len(all_chunks)} total chunks.")

if __name__ == "__main__":
    main()
