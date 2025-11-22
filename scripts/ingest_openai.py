#!/usr/bin/env python3
"""
FINAL ingestion with all fixes:
- OpenAI tiktoken tokenizer
- Debug logging for Docling labels
- Flexible image/table matching
""" 
import sys
import os
from pathlib import Path

# Set environment for OpenAI tokenizer BEFORE imports
os.environ["USE_TIKTOKEN"] = "1"
os.environ["EMB_MODEL"] = "text-embedding-3-small"

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
    # Also load runtime config
    load_dotenv(".env.runtime")
except ImportError:
    pass

import logging
import json
import subprocess
import time
import gc

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

def main():
    """Full ingestion with OpenAI tokenizer."""
    # Reset database
    logger.info("🔄 Resetting chunks table...")
    from rag.store.sqlite_store import get_db_connection
    with get_db_connection() as conn:
        conn.execute("DELETE FROM chunks")
        conn.execute("UPDATE documents SET status='downloaded' WHERE status='processed' OR status='failed'")
        conn.commit()
    
    docs = get_documents_by_status('downloaded')
    logger.info(f"📚 Processing {len(docs)} documents with OpenAI tiktoken")
    
    for idx, doc in enumerate(docs, 1):
        pdf_path = Path("data/raw") / doc['filename']
        
        if not pdf_path.exists():
            logger.warning(f"⏭️  Skipping {doc['filename']} (not found)")
            continue
        
        try:
            logger.info(f"[{idx}/{len(docs)}] Processing: {doc['title'][:60]}...")
            
            # Parse with Docling
            parsed = parse_pdf_multimodal(str(pdf_path))
            
            # Convert to records
            records = elements_to_records(
                parsed, 
                doc['id'], 
                extra_meta={"title": doc['title'], "filename": doc['filename']}
            )
            logger.info(f"  📄 Extracted {len(records)} elements")
            
            del parsed
            gc.collect()
            
            # Chunk with OpenAI tokenizer
            doc_chunks = []
            for rec in records:
                try:
                    chunks = chunk_record_semantic(rec)
                    doc_chunks.extend(chunks)
                except Exception as e:
                    logger.warning(f"  ⚠️  Chunking failed for record: {e}")
                    continue
            
            logger.info(f"  ✂️  Generated {len(doc_chunks)} chunks")
            
            # Save to SQLite
            if doc_chunks:
                insert_chunks(doc_chunks)
                update_document_status(doc['id'], 'processed')
                logger.info(f"  ✅ Saved to SQLite")
            
            del records, doc_chunks
            gc.collect()
            time.sleep(1)  # Small delay
            
        except Exception as e:
            logger.error(f"❌ Failed to process {doc['filename']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Export and rebuild index
    logger.info("\n🔨 Rebuilding search index...")
    chunks_path = Path("data/staging/chunks.jsonl")
    all_chunks = get_all_chunks()
    
    logger.info(f"📦 Exporting {len(all_chunks)} chunks to JSONL...")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    python_exe = sys.executable
    
    logger.info("🔮 Building embeddings with OpenAI...")
    subprocess.run(
        f"{python_exe} -m scripts.build_embeddings --chunks {chunks_path} "
        f"--out_vecs data/embeddings/embeddings.npy --out_ids data/embeddings/ids.npy "
        f"--model text-embedding-3-small --adapter openai --batch 256 --normalize",
        shell=True, check=True
    )
    
    logger.info("🗂️  Building FAISS index...")
    subprocess.run(
        f"{python_exe} -m scripts.build_faiss --vecs data/embeddings/embeddings.npy "
        f"--index_out data/embeddings/vectors.faiss",
        shell=True, check=True
    )
    
    logger.info(f"\n✅ Complete! Indexed {len(all_chunks)} chunks with OpenAI embeddings.")

if __name__ == "__main__":
    main()
