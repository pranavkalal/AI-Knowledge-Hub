from dataclasses import dataclass
from typing import Optional, Dict
from pypdf import PdfReader  # pypdf works cross-platform
import datetime
import os

@dataclass
class ParsedPDF:
    text: str
    meta: Dict[str, str]

def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    chunks = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        chunks.append(txt)
    return "\n".join(chunks).strip()

def parse_pdf(pdf_path: str, extra_meta: Optional[Dict[str, str]] = None) -> ParsedPDF:
    text = extract_text(pdf_path)
    stat = os.stat(pdf_path)
    meta = {
        "filename": os.path.basename(pdf_path),
        "path": pdf_path,
        "size_bytes": str(stat.st_size),
        "mtime": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
    if extra_meta:
        meta.update({k: str(v) for k, v in extra_meta.items() if v is not None})
    return ParsedPDF(text=text, meta=meta)
