# rag/ingest_lib/download.py
import hashlib, os, time
from typing import Optional
import requests

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def safe_filename(url: str) -> str:
    name = url.split("/")[-1].split("?")[0]
    return name[:180] or "file.pdf"

def ensure_dir(path: str):
    # If a file exists where the dir should be, complain clearly.
    if os.path.exists(path) and not os.path.isdir(path):
        raise RuntimeError(f"download_dir points to a file, not a directory: {path}. "
                           f"Delete it and create a folder.")
    os.makedirs(path, exist_ok=True)

def download_pdf(url: str, dest_dir: str, timeout: int, user_agent: str,
                 attempts: int, backoff: int) -> Optional[str]:
    ensure_dir(dest_dir)
    headers = {"User-Agent": user_agent}
    for i in range(attempts):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "")
            if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
                return None
            content = r.content
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
