#!/usr/bin/env python3
"""
Process a single batch of documents (max 5), then exit.
This clears all memory between batches.
"""
import os
# Set before any imports
os.environ["USE_TIKTOKEN"] = "1"
os.environ["DOCLING_DEVICE"] = "cpu"  # Force CPU to avoid MPS memory spikes

import gc
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rag.ingest.parsers.docling_parser import parse_pdf_multimodal, elements_to_records
from rag.ingest.chunkers.semantic import chunk_record_semantic  
from rag.store.sqlite_store import get_documents_by_status, insert_chunks, update_document_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(batch_size=5):
    """Process up to batch_size documents."""
    docs = get_documents_by_status('downloaded')[:batch_size]
    
    if not docs:
        logger.info("No documents to process")
        return 0
    
    logger.info(f"Processing {len(docs)} documents in this batch")
    
    success_count = 0
    for idx, doc in enumerate(docs, 1):
        pdf_path = Path("data/raw") / doc['filename']
        if not pdf_path.exists():
            logger.warning(f"[{idx}/{len(docs)}] File not found: {pdf_path}")
            continue
        
        try:
            logger.info(f"[{idx}/{len(docs)}] Processing: {doc['title'][:60]}...")
            
            # Parse with Docling
            parsed = parse_pdf_multimodal(str(pdf_path))
            logger.info(f"  Extracted {len(parsed.elements)} elements")
            
            # Convert to records
            records = elements_to_records(parsed, doc['id'], extra_meta={
                "title": doc['title'],
                "filename": doc['filename']
            })
            
            del parsed
            gc.collect()
            
            # Chunk
            chunks = []
            for rec in records:
                try:
                    chunks.extend(chunk_record_semantic(rec))
                except Exception as e:
                    logger.warning(f"  Chunking failed for record: {e}")
            
            logger.info(f"  Generated {len(chunks)} chunks")
            
            # Save
            if chunks:
                insert_chunks(chunks)
                update_document_status(doc['id'], 'processed')
                logger.info(f"  ✅ Saved to database")
                success_count += 1
            
            del records, chunks
            gc.collect()
            
        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info(f"\nBatch complete: {success_count}/{len(docs)} succeeded")
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
