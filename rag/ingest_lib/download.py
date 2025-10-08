import hashlib
import os
import time
from typing import Optional

import requests

PDF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Accept": "application/pdf,*/*;q=0.8",
}

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def safe_filename(url: str) -> str:
    name = url.split("/")[-1].split("?")[0] or "file.pdf"
    # keep Windows happy re: invalid chars and path length
    name = name.replace(":", "_").replace("*", "_").replace("?", "_").replace("|", "_").replace("<", "_").replace(">", "_").replace("\"", "_")
    return name[:180]  # trim ridiculously long names

def ensure_dir(path: str):
    if os.path.exists(path) and not os.path.isdir(path):
        raise RuntimeError(f"download_dir points to a file, not a directory: {path}. Delete it and create a folder.")
    os.makedirs(path, exist_ok=True)

def download_pdf(url: str, dest_dir: str, timeout: int, user_agent: str,
                 attempts: int, backoff: int) -> Optional[str]:
    ensure_dir(dest_dir)
    for i in range(attempts):
        try:
            with requests.get(url, headers=PDF_HEADERS, timeout=timeout, stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                ct = (r.headers.get("Content-Type") or "").lower()
                if "pdf" not in ct and not url.lower().endswith(".pdf"):
                    return None
                content = b""
                for chunk in r.iter_content(chunk_size=1 << 15):
                    if chunk:
                        content += chunk
                hexd = sha256_bytes(content)[:12]
                fname = f"{hexd}_{safe_filename(url)}"
                fpath = os.path.join(dest_dir, fname)
                if not os.path.exists(fpath):
                    with open(fpath, "wb") as f:
                        f.write(content)
                return fpath
        except Exception:
            if i == attempts - 1:
                return None
            time.sleep(backoff * (i + 1))
    return None
