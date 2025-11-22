#!/usr/bin/env python3
"""
Excel-driven ingestion script for CRDC metadata.
Reads metadata from Excel, downloads PDFs, and populates SQLite database.
"""

import sys
import logging
from pathlib import Path
from typing import Optional
import requests
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.store.sqlite_store import init_db, insert_document, get_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
EXCEL_PATH = Path("CRDC Metadata 2020-2025 .xlsx")
PDF_DIR = Path("data/raw")


def extract_year(date_str: Optional[str]) -> Optional[int]:
    """Extract year from date string (handles various formats)."""
    if not date_str or pd.isna(date_str):
        return None
    
    # Try to parse as datetime
    try:
        if isinstance(date_str, (int, float)):
            return int(date_str)
        date_str = str(date_str).strip()
        # Try common formats
        for fmt in ["%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.year
            except ValueError:
                continue
        # If it's just a 4-digit year
        if len(date_str) == 4 and date_str.isdigit():
            return int(date_str)
    except (ValueError, AttributeError):
        pass
    
    return None


def download_pdf(url: str, output_path: Path) -> bool:
    """
    Download PDF from URL to output_path.
    
    Returns:
        True if successful, False otherwise
    """
    if output_path.exists():
        logger.info(f"  PDF already exists: {output_path.name}")
        return True
    
    try:
        logger.info(f"  Downloading from {url[:80]}...")
        
        # Add headers to avoid 415 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*'
        }
        
        response = requests.get(url, timeout=30, stream=True, headers=headers)
        response.raise_for_status()
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"  ✅ Downloaded: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"  ❌ Download failed: {e}")
        return False


def ingest_excel(
    excel_path: Path = EXCEL_PATH,
    pdf_dir: Path = PDF_DIR,
    limit: Optional[int] = None
):
    """
    Main ingestion function.
    
    Args:
        excel_path: Path to Excel file
        pdf_dir: Directory to save PDFs
        limit: Limit number of rows to process (for testing)
    """
    if not excel_path.exists():
        logger.error(f"Excel file not found: {excel_path}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Read Excel
    logger.info(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    if limit:
        df = df.head(limit)
        logger.info(f"Processing first {limit} rows (test mode)")
    
    logger.info(f"Found {len(df)} documents to process\n")
    
    # Track stats
    stats = {
        'total': len(df),
        'skipped': 0,
        'downloaded': 0,
        'registered': 0,
        'failed': 0
    }
    
    # Process each row
    for idx, row in df.iterrows():
        doc_id = str(row.get('uuid', '')).strip()
        title = str(row.get('title', '')).strip()
        source_url = str(row.get('field_files', '')).strip()
        
        logger.info(f"[{idx+1}/{len(df)}] Processing: {title[:60]}...")
        
        # Validate required fields
        if not doc_id or pd.isna(row.get('uuid')):
            logger.warning(f"  ⚠️  Skipping: No UUID")
            stats['skipped'] += 1
            continue
        
        if not source_url or pd.isna(row.get('field_files')) or source_url == 'nan':
            logger.warning(f"  ⚠️  Skipping: No PDF URL")
            stats['skipped'] += 1
            continue
        
        # Check if already processed
        existing_doc = get_document(doc_id)
        if existing_doc and existing_doc['status'] == 'processed':
            logger.info(f"  ⏭️  Already processed, skipping")
            stats['skipped'] += 1
            continue
        
        # Download PDF
        pdf_path = pdf_dir / f"{doc_id}.pdf"
        download_success = download_pdf(source_url, pdf_path)
        
        if download_success:
            stats['downloaded'] += 1
            file_size = pdf_path.stat().st_size if pdf_path.exists() else None
        else:
            stats['failed'] += 1
            file_size = None
        
        # Register in database
        try:
            insert_document(
                doc_id=doc_id,
                title=title or "Untitled",
                source_url=source_url,
                filename=f"{doc_id}.pdf",
                year=extract_year(row.get('field_date_issued')),
                authors=str(row.get('field_author', '')).strip() if pd.notna(row.get('field_author')) else None,
                categories=str(row.get('field_subject', '')).strip() if pd.notna(row.get('field_subject')) else None,
                description=str(row.get('field_abstract', '')).strip() if pd.notna(row.get('field_abstract')) else None,
                publisher=str(row.get('field_publisher', '')).strip() if pd.notna(row.get('field_publisher')) else None,
                document_type=str(row.get('type', '')).strip() if pd.notna(row.get('type')) else None,
                uid=str(row.get('uid', '')).strip() if pd.notna(row.get('uid')) else None,
                alternative_title=str(row.get('field_alternative_title', '')).strip() if pd.notna(row.get('field_alternative_title')) else None,
                file_size=file_size,
                # Additional metadata
                field_collections=str(row.get('field_collections', '')).strip() if pd.notna(row.get('field_collections')) else None,
                field_copyright=str(row.get('field_copyright', '')).strip() if pd.notna(row.get('field_copyright')) else None,
                field_identifier=str(row.get('field_identifier', '')).strip() if pd.notna(row.get('field_identifier')) else None,
            )
            stats['registered'] += 1
            logger.info(f"  ✅ Registered in database")
            
        except Exception as e:
            logger.error(f"  ❌ Database error: {e}")
            stats['failed'] += 1
        
        print()  # Blank line for readability
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("INGESTION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total documents:     {stats['total']}")
    logger.info(f"Registered in DB:    {stats['registered']}")
    logger.info(f"PDFs downloaded:     {stats['downloaded']}")
    logger.info(f"Skipped:             {stats['skipped']}")
    logger.info(f"Failed:              {stats['failed']}")
    logger.info("="*60)
    logger.info("\n✅ Excel ingestion complete!")
    logger.info(f"Next step: Run 'python scripts/ingest_docling.py' to parse PDFs")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest CRDC metadata from Excel")
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process (for testing)"
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=EXCEL_PATH,
        help="Path to Excel file"
    )
    
    args = parser.parse_args()
    
    ingest_excel(
        excel_path=args.excel,
        limit=args.limit
    )
