# rag/ingest_lib/download.py
"""
PDF downloader with clean filename handling.
"""

import requests
import time
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote
import re

# Import for type hints
try:
    from .discover import ReportMetadata
except ImportError:
    ReportMetadata = None


def sanitize_filename(name: str) -> str:
    """Convert string to a safe filename."""
    # URL decode first
    name = unquote(name)
    # Remove/replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = re.sub(r'\s+', '_', safe.strip())
    # Limit length
    if len(safe) > 150:
        safe = safe[:150]
    # Ensure .pdf extension
    if not safe.lower().endswith('.pdf'):
        safe = safe + '.pdf'
    return safe


def download_pdf(
    source: Union[str, "ReportMetadata"], 
    download_dir: str, 
    timeout: int = 30, 
    user_agent: str = "CRDC-Knowledge-Hub/0.1", 
    attempts: int = 3, 
    backoff: int = 2
) -> Optional[str]:
    """
    Download a PDF and save with a clean filename.
    
    Args:
        source: Either a URL string or a ReportMetadata object
        download_dir: Directory to save the PDF
        timeout: Request timeout in seconds
        user_agent: User agent for requests
        attempts: Number of retry attempts
        backoff: Backoff multiplier for retries
    
    Returns:
        Path to downloaded file, or None if download failed
    """
    headers = {"User-Agent": user_agent}
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    # Handle both URL string and ReportMetadata
    if hasattr(source, 'pdf_url'):
        # It's a ReportMetadata object
        url = source.pdf_url
        filename = source.get_filename()
    else:
        # It's a URL string
        url = source
        # Extract filename from URL
        raw_name = url.split("/")[-1].split("?")[0]
        filename = sanitize_filename(raw_name)
    
    out_path = Path(download_dir) / filename
    
    # Check if already exists
    if out_path.exists():
        print(f"[skip] Already exists: {filename}")
        return str(out_path)
    
    # Download with retries
    for attempt in range(attempts):
        try:
            print(f"[download] {filename}...")
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
            resp.raise_for_status()
            
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"[success] Saved: {filename}")
            return str(out_path)
            
        except Exception as e:
            print(f"[warn] Download failed (attempt {attempt + 1}/{attempts}): {e}")
            if attempt < attempts - 1:
                sleep_time = backoff * (attempt + 1)
                print(f"[retry] Waiting {sleep_time}s before retry...")
                time.sleep(sleep_time)
    
    print(f"[error] Failed to download: {url}")
    return None


def download_reports(
    reports: list,
    download_dir: str,
    timeout: int = 30,
    user_agent: str = "CRDC-Knowledge-Hub/0.1"
) -> list:
    """
    Download multiple reports.
    
    Args:
        reports: List of ReportMetadata objects
        download_dir: Directory to save PDFs
        timeout: Request timeout
        user_agent: User agent string
    
    Returns:
        List of successfully downloaded file paths
    """
    downloaded = []
    
    for report in reports:
        path = download_pdf(
            source=report,
            download_dir=download_dir,
            timeout=timeout,
            user_agent=user_agent
        )
        if path:
            downloaded.append(path)
        
        # Be polite
        time.sleep(0.5)
    
    return downloaded
