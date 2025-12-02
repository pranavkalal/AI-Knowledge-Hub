# rag/ingest_lib/download.py
import requests
import time
from pathlib import Path
from typing import Optional

def download_pdf(url: str, download_dir: str, timeout: int = 20, user_agent: str = "CRDC-Ingest", attempts: int = 3, backoff: int = 2) -> Optional[str]:
    headers = {"User-Agent": user_agent}
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    # Use a safe filename
    safe_name = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.')).strip()
    if not safe_name:
        safe_name = f"doc_{hash(url)}.pdf"
        
    out_path = Path(download_dir) / safe_name
    
    if out_path.exists():
        return str(out_path)
        
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
            resp.raise_for_status()
            
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return str(out_path)
        except Exception as e:
            print(f"[warn] download failed (attempt {attempt+1}): {e}")
            time.sleep(backoff * (attempt + 1))
            
    return None
