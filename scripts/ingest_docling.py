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

def ingest_data_raw():
    raw_dir = Path("data/raw")
    chunks_path = Path("data/staging/chunks.jsonl")
    
    if not raw_dir.exists():
        logger.error(f"Directory not found: {raw_dir}")
        return

    pdfs = list(raw_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No PDFs found in {raw_dir}")
        return

    logger.info(f"Found {len(pdfs)} PDFs in {raw_dir}")
    
    # Ensure staging dir exists
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    
    all_chunks = []

    # Process PDFs one by one to save memory
    import gc
    
    # Limit to 5 PDFs for now to prevent hanging
    pdfs = pdfs[:5] 
    logger.info(f"Processing first {len(pdfs)} PDFs to avoid memory issues...")

    for pdf_path in pdfs:
        try:
            logger.info(f"Processing {pdf_path.name}...")
            
            # 1. Parse with Docling
            # Re-initialize converter per file if needed, or just rely on scope
            parsed = parse_pdf_multimodal(str(pdf_path))
            
            # 2. Convert to records
            doc_id = pdf_path.stem.replace(" ", "_")
            records = elements_to_records(
                parsed, 
                doc_id, 
                extra_meta={
                    "title": pdf_path.stem,
                    "filename": pdf_path.name
                }
            )
            logger.info(f"  Extracted {len(records)} elements")
            
            # Clear parsed object to free memory
            del parsed
            gc.collect()

            # 3. Chunk (Semantic)
            doc_chunks = []
            for rec in records:
                chunks = chunk_record_semantic(rec)
                doc_chunks.extend(chunks)
            
            logger.info(f"  Generated {len(doc_chunks)} chunks")
            all_chunks.extend(doc_chunks)
            
            # Clear records
            del records
            del doc_chunks
            gc.collect()
                
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    if not all_chunks:
        logger.warning("No chunks generated. Exiting.")
        return

    # 4. Write chunks to JSONL
    logger.info(f"Writing {len(all_chunks)} chunks to {chunks_path}...")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # 5. Run Embedding and FAISS build
    logger.info("Building embeddings...")
    # Using default paths from tasks.py
    emb_eds = "data/embeddings/embeddings.npy"
    emb_ids = "data/embeddings/ids.npy"
    faiss_idx = "data/embeddings/vectors.faiss"
    
    # Ensure embeddings dir exists
    Path(emb_eds).parent.mkdir(parents=True, exist_ok=True)

    # Call build_embeddings
    # Using OpenAI embeddings
    # Call build_embeddings
    # Using OpenAI embeddings to match runtime config
    run_command(f"{sys.executable} -m scripts.build_embeddings --chunks {chunks_path} --out_vecs {emb_eds} --out_ids {emb_ids} --model text-embedding-3-small --adapter openai --batch 256 --normalize")
    
    # Call build_faiss
    logger.info("Building FAISS index...")
    run_command(f"{sys.executable} -m scripts.build_faiss --vecs {emb_eds} --index_out {faiss_idx}")

    logger.info(f"\n✅ Ingestion Complete! Indexed {len(all_chunks)} chunks from {len(pdfs)} documents.")

if __name__ == "__main__":
    ingest_data_raw()
