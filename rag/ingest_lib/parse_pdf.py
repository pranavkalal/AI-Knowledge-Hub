# rag/ingest_lib/parse_pdf.py
from typing import Dict, Any
from dataclasses import dataclass, field

@dataclass
class ParsedDoc:
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)

def parse_pdf(pdf_path: str, extra_meta: Dict[str, Any] = None) -> ParsedDoc:
    """
    Default PDF parser using pypdf if available.
    """
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except ImportError:
        print("[warn] pypdf not installed, skipping text extraction for default parser")
        text = "Text extraction unavailable (install pypdf)"
    except Exception as e:
        print(f"[warn] failed to parse {pdf_path}: {e}")
        
    meta = extra_meta or {}
    meta["filename"] = str(pdf_path)
    return ParsedDoc(text=text, meta=meta)
