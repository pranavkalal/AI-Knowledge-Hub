
import os
import sys
import json
import logging
from typing import List
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.vector_postgres import PostgresStoreAdapter

# Mock Embedder
class MockEmbedder:
    def embed_query(self, text: str) -> List[float]:
        # Return a dummy embedding of size 1536
        return [0.1] * 1536

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Ensure connection string is set (mock if needed for local test without real DB, 
    # but here we assume the user has a DB or we fail gracefully)
    if not os.environ.get("POSTGRES_CONNECTION_STRING"):
        logger.error("POSTGRES_CONNECTION_STRING not set. Skipping test.")
        return

    logger.info("Initializing PostgresStoreAdapter...")
    store = PostgresStoreAdapter(table_name="test_chunks", embedder=MockEmbedder())

    # 1. Insert Test Data
    logger.info("Inserting test data...")
    chunks = [
        {
            "id": "doc1_chunk1",
            "doc_id": "doc1",
            "chunk_index": 0,
            "text": "The quick brown fox jumps over the lazy dog.",
            "metadata": {"year": 2023, "title": "Fox Story"}
        },
        {
            "id": "doc2_chunk1",
            "doc_id": "doc2",
            "chunk_index": 0,
            "text": "A fast brown fox leaps over a sleepy canine.",
            "metadata": {"year": 2022, "title": "Canine Story"}
        },
        {
            "id": "doc3_chunk1",
            "doc_id": "doc3",
            "chunk_index": 0,
            "text": "Apples and oranges are fruits.",
            "metadata": {"year": 2023, "title": "Fruit Story"}
        }
    ]
    embeddings = [[0.1] * 1536 for _ in chunks] # Dummy embeddings
    store.add_documents(chunks, embeddings)
    logger.info("Data inserted.")

    # 2. Test Hybrid Search (Keyword Boost)
    logger.info("\n--- Test 1: Hybrid Search (Keyword 'canine') ---")
    # 'canine' is in doc2 but not doc1. Vector scores are identical (dummy embeddings).
    # Keyword score should boost doc2.
    results = store.search_raw("canine", top_k=5)
    for res in results:
        logger.info(f"ID: {res['id']}, Score: {res['score']:.4f} (V: {res.get('vector_score', 0):.4f}, K: {res.get('keyword_score', 0):.4f})")
    
    # Verify doc2 is first
    if results and results[0]['id'] == 'doc2_chunk1':
        logger.info("✅ Hybrid Search Passed: 'canine' boosted doc2.")
    else:
        logger.warning("❌ Hybrid Search Failed: doc2 not top result.")

    # 3. Test Metadata Filtering
    logger.info("\n--- Test 2: Metadata Filtering (year >= 2023) ---")
    filters = {"year_min": 2023}
    results = store.search_raw("fox", top_k=5, filters=filters)
    for res in results:
        logger.info(f"ID: {res['id']}, Year: {res['metadata'].get('year')}")
    
    # Verify only 2023 docs (doc1, doc3) are returned
    ids = [r['id'] for r in results]
    if 'doc2_chunk1' not in ids and 'doc1_chunk1' in ids:
        logger.info("✅ Metadata Filtering Passed: Excluded 2022 doc.")
    else:
        logger.warning(f"❌ Metadata Filtering Failed: Got {ids}")

    # Cleanup (Optional)
    # with store.engine.connect() as conn:
    #     conn.execute(text("DROP TABLE test_chunks"))
    #     conn.commit()

if __name__ == "__main__":
    main()
