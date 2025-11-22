#!/usr/bin/env python3
"""
Batched ingestion orchestrator.
Processes documents in batches of 5 with full Python restart between batches.
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag.store.sqlite_store import get_documents_by_status, get_all_chunks
import json

BATCH_SIZE = 5

def main():
    print("🔍 Checking for documents to process...\n")
    
    docs = get_documents_by_status('downloaded')
    
    if not docs:
        print("✅ No documents need processing")
        print("\n🔨 Rebuilding index from existing chunks...")
        rebuild_index()
        return
    
    total_batches = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"📚 Found {len(docs)} documents")
    print(f"🔄 Will process in {total_batches} batches of {BATCH_SIZE}\n")
    
    # Process batches
    for batch_num in range(total_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(docs))
        
        print(f"\n{'='*60}")
        print(f"BATCH {batch_num + 1}/{total_batches}")
        print(f"Documents {start_idx + 1}-{end_idx} of {len(docs)}")
        print(f"{'='*60}\n")
        
        # Run batch processor as separate process
        result = subprocess.run([
            sys.executable,
            "scripts/ingestion/_process_batch.py"
        ], cwd=Path(__file__).parent.parent.parent)
        
        if result.returncode != 0:
            print(f"\n⚠️  Batch {batch_num + 1} had errors, but continuing...\n")
        else:
            print(f"\n✅ Batch {batch_num + 1} completed successfully\n")
    
    print(f"\n{'='*60}")
    print("All batches processed!")
    print(f"{'='*60}\n")
    
    # Rebuild index
    print("🔨 Rebuilding search index...\n")
    rebuild_index()
    
    print("\n🎉 Ingestion complete!")

def rebuild_index():
    """Export chunks and rebuild embeddings + FAISS."""
    from rag.store.sqlite_store import get_all_chunks
    
    # Export to JSONL
    chunks_path = Path("data/staging/chunks.jsonl")
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    
    all_chunks = get_all_chunks()
    print(f"📦 Exporting {len(all_chunks)} chunks to JSONL...")
    
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    # Build embeddings
    print("🔮 Building embeddings...")
    subprocess.run([
        sys.executable, "-m", "scripts.indexing.build_embeddings",
        "--chunks", str(chunks_path),
        "--out_vecs", "data/embeddings/embeddings.npy",
        "--out_ids", "data/embeddings/ids.npy",
        "--model", "text-embedding-3-small",
        "--adapter", "openai",
        "--batch", "256",
        "--normalize"
    ], check=True)
    
    # Build FAISS
    print("🗂️  Building FAISS index...")
    subprocess.run([
        sys.executable, "-m", "scripts.indexing.build_faiss",
        "--vecs", "data/embeddings/embeddings.npy",
        "--index_out", "data/embeddings/vectors.faiss"
    ], check=True)
    
    print(f"✅ Index built with {len(all_chunks)} chunks")

if __name__ == "__main__":
    main()
