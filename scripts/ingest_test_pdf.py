#!/usr/bin/env python3
"""
Test script to ingest a sample PDF with Docling for Deep Linking verification.
"""

import sys
import os
from pathlib import Path
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.ingest_lib.parse_docling import parse_pdf_multimodal, elements_to_records
from rag.segment.semantic_chunker import chunk_record_semantic
from rag.ingest_lib.store import VectorStore

def ingest_sample_pdf():
    # 1. Get a sample PDF
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "sample_invoice.pdf"
    
    if not pdf_path.exists():
        print("Downloading sample PDF...")
        # Use a sample invoice or technical doc that has tables/images
        url = "https://github.com/DS4SD/docling/raw/main/tests/data/2206.01062.pdf" # Docling paper itself
        response = requests.get(url)
        pdf_path.write_bytes(response.content)
        print(f"Downloaded to {pdf_path}")

    # 2. Parse with Docling
    print(f"Parsing {pdf_path} with Docling...")
    parsed = parse_pdf_multimodal(str(pdf_path))
    
    # 3. Convert to records
    doc_id = "docling_test_001"
    records = elements_to_records(parsed, doc_id, extra_meta={"title": "Docling Test Paper"})
    print(f"Extracted {len(records)} elements")

    # 4. Chunk (Semantic)
    print("Chunking...")
    all_chunks = []
    for rec in records:
        # For elements, we might not need further chunking if they are small,
        # but let's run them through to be safe and get token counts
        chunks = chunk_record_semantic(rec)
        all_chunks.extend(chunks)
    
    print(f"Generated {len(all_chunks)} chunks")

    # 5. Index
    print("Indexing to FAISS...")
    store = VectorStore()
    store.add_documents(all_chunks)
    
    print("\n✅ Ingestion Complete!")
    print(f"Document ID: {doc_id}")
    print("You can now ask questions about 'Docling' in the chat.")

if __name__ == "__main__":
    ingest_sample_pdf()
