#!/usr/bin/env python3
import sys
import os
import logging
import json
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found, environment variables might be missing.")

from rag.store.sqlite_store import get_all_chunks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd):
    logger.info(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def finalize():
    chunks_path = Path("data/staging/chunks.jsonl")
    
    logger.info("Exporting all chunks from SQLite to JSONL...")
    all_db_chunks = get_all_chunks()
    logger.info(f"Found {len(all_db_chunks)} chunks in SQLite.")
    
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_db_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    logger.info("Building embeddings...")
    emb_eds = "data/embeddings/embeddings.npy"
    emb_ids = "data/embeddings/ids.npy"
    faiss_idx = "data/embeddings/vectors.faiss"
    
    Path(emb_eds).parent.mkdir(parents=True, exist_ok=True)
    python_exe = sys.executable
    
    # Ensure we use the correct adapter and model
    run_command(f"{python_exe} -m scripts.build_embeddings --chunks {chunks_path} --out_vecs {emb_eds} --out_ids {emb_ids} --model text-embedding-3-small --adapter openai --batch 256 --normalize")
    
    logger.info("Building FAISS index...")
    run_command(f"{python_exe} -m scripts.build_faiss --vecs {emb_eds} --index_out {faiss_idx}")

    logger.info("Done!")

if __name__ == "__main__":
    finalize()
