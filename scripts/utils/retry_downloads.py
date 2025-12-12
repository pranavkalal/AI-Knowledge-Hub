#!/usr/bin/env python3
"""
Retry failed PDF downloads from the database.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.store.sqlite_store import get_db_connection
from scripts.ingest_excel import download_pdf, PDF_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry_failed_downloads():
    """Retry downloading PDFs for documents with status='pending' (failed downloads)."""
    
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT id, title, source_url, filename 
            FROM documents 
            WHERE status = 'pending'
        """)
        failed_docs = cursor.fetchall()
    
    if not failed_docs:
        logger.info("✅ No failed downloads to retry!")
        return
    
    logger.info(f"Found {len(failed_docs)} documents with failed downloads")
    logger.info("Retrying...\n")
    
    stats = {'success': 0, 'failed': 0}
    
    for doc in failed_docs:
        doc_id = doc['id']
        title = doc['title']
        source_url = doc['source_url']
        filename = doc['filename']
        
        logger.info(f"Retrying: {title[:60]}...")
        
        pdf_path = PDF_DIR / filename
        success = download_pdf(source_url, pdf_path)
        
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
        print()
    
    logger.info("\n" + "="*60)
    logger.info("RETRY SUMMARY")
    logger.info("="*60)
    logger.info(f"Successful:  {stats['success']}")
    logger.info(f"Failed:      {stats['failed']}")
    logger.info("="*60)


if __name__ == "__main__":
    retry_failed_downloads()
