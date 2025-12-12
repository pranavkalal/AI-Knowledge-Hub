#!/usr/bin/env python3
"""
Test Docling multi-modal PDF parsing.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.ingest_lib.parse_docling import parse_pdf_multimodal, elements_to_records


def test_docling_parser(pdf_path: str):
    """Test Docling parser on a sample PDF."""
    print(f"\n{'='*70}")
    print(f"Testing Docling Parser on: {pdf_path}")
    print(f"{'='*70}\n")
    
    try:
        # Parse PDF
        parsed = parse_pdf_multimodal(pdf_path)
        
        # Print metadata
        print("📄 Metadata:")
        for key, value in parsed.metadata.items():
            print(f"  {key}: {value}")
        
        # Print element summary
        print(f"\n📊 Elements ({len(parsed.elements)} total):")
        
        element_types = {}
        for elem in parsed.elements:
            element_types[elem.type] = element_types.get(elem.type, 0) + 1
        
        for elem_type, count in element_types.items():
            print(f"  {elem_type}: {count}")
        
        # Show sample elements
        print(f"\n📝 Sample Elements:")
        for i, elem in enumerate(parsed.elements[:5], 1):
            print(f"\n  Element {i} ({elem.type}, page {elem.page}):")
            print(f"    Text: {elem.text[:100]}...")
            if elem.bbox:
                print(f"    BBox: {elem.bbox}")
            if elem.image_path:
                print(f"    Image: {elem.image_path}")
        
        # Convert to records
        records = elements_to_records(parsed, "test_doc_001")
        print(f"\n📦 Generated {len(records)} records for chunking")
        
        # Show sample record
        if records:
            print(f"\n  Sample Record:")
            sample = records[0]
            for key, value in sample.items():
                if key == "text":
                    print(f"    {key}: {str(value)[:80]}...")
                else:
                    print(f"    {key}: {value}")
        
        print(f"\n{'='*70}")
        print("✅ Docling parser test completed successfully!")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test with a sample PDF (you can replace with your own)
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Try to find a sample PDF in data/pdfs
        pdf_dir = Path("data/pdfs")
        if pdf_dir.exists():
            pdfs = list(pdf_dir.glob("*.pdf"))
            if pdfs:
                pdf_path = str(pdfs[0])
            else:
                print("No PDFs found in data/pdfs/")
                print("Usage: python scripts/test_docling_parser.py <path_to_pdf>")
                sys.exit(1)
        else:
            print("Usage: python scripts/test_docling_parser.py <path_to_pdf>")
            sys.exit(1)
    
    test_docling_parser(pdf_path)
