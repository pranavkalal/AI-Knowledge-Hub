import argparse
import logging
import sys
from pathlib import Path

import faiss
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Build FAISS index from embeddings")
    parser.add_argument("--embeddings", required=True, help="Path to embeddings .npy file")
    parser.add_argument("--ids", required=True, help="Path to ids .npy file")
    parser.add_argument("--out_index", required=True, help="Path to save FAISS index")
    args = parser.parse_args()

    emb_path = Path(args.embeddings)
    ids_path = Path(args.ids)
    out_path = Path(args.out_index)

    if not emb_path.exists():
        logger.error(f"Embeddings file not found: {emb_path}")
        sys.exit(1)
    
    if not ids_path.exists():
        logger.error(f"IDs file not found: {ids_path}")
        sys.exit(1)

    # Load data
    logger.info(f"Loading embeddings from {emb_path}...")
    embeddings = np.load(str(emb_path))
    ids = np.load(str(ids_path), allow_pickle=True)

    if len(embeddings) != len(ids):
        logger.error(f"Mismatch: {len(embeddings)} embeddings vs {len(ids)} IDs")
        sys.exit(1)

    dim = embeddings.shape[1]
    count = embeddings.shape[0]
    logger.info(f"Loaded {count} vectors of dimension {dim}")

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build Index
    # Using IndexFlatIP (Inner Product) which is equivalent to Cosine Similarity for normalized vectors
    # OpenAI embeddings are normalized, so IP is correct.
    logger.info("Building IndexFlatIP...")
    index = faiss.IndexFlatIP(dim)
    
    # Add vectors
    index.add(embeddings)
    
    # Save
    logger.info(f"Saving index to {out_path}...")
    faiss.write_index(index, str(out_path))
    
    # Save ID mapping (optional, but good practice if needed separately)
    # For now, we assume the index in FAISS corresponds to the index in the IDs array
    # which is handled by the store adapter.
    
    logger.info("✅ FAISS index built successfully")

if __name__ == "__main__":
    main()
