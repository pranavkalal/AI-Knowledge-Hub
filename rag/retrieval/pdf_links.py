from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

# Remove JSONL dependency
PDF_ROOT = Path(os.environ.get("PDF_ROOT", "data/raw")).resolve()


def _default_filename(doc_id: str) -> Optional[str]:
    """Return `<doc_id>.pdf` if that file exists under the PDF root."""
    if not doc_id:
        return None
    candidate = (PDF_ROOT / f"{doc_id}.pdf").resolve()
    try:
        candidate.relative_to(PDF_ROOT)
    except ValueError:
        return None
    if candidate.exists():
        return candidate.name
    return None


def get_pdf_filename(doc_id: str) -> Optional[str]:
    """Return the stored filename for doc_id, falling back to `<doc_id>.pdf`."""
    if not doc_id:
        return None

    # Use filesystem lookup (Postgres adapter handles metadata separately)
    filename = _default_filename(doc_id)
    if filename:
        return filename
        
    # Try stripping chunk suffix (e.g. _p1_0)
    # Format is {doc_id}_p{page}_{index}
    if "_p" in doc_id:
        base_id = doc_id.rsplit("_p", 1)[0]
        return _default_filename(base_id)
        
    return None


def build_pdf_url(doc_id: str, page: Optional[int] = None, filename: Optional[str] = None) -> Optional[str]:
    """Construct the served PDF URL for a document id."""
    if not doc_id:
        return None
    
    if not filename:
        filename = get_pdf_filename(doc_id)
        
    if not filename:
        return None
        
    if filename:
        base = f"/api/pdf/{filename}"
    else:
        base = f"/pdf/by-id/{doc_id}"
        
    if page is None:
        return base
    page_num = max(1, int(page))
    return f"{base}#page={page_num}"


def _coerce_page(page: Any) -> Optional[int]:
    if isinstance(page, list) and page:
        page = page[0]
    if page in (None, "", []):
        return None
    try:
        return max(1, int(page))
    except (TypeError, ValueError):
        return None


def enrich_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mutate and return metadata with filename, rel_path, source_url, and url fields populated.
    """
    doc_id = str(meta.get("doc_id") or "").strip()
    if not doc_id:
        return meta

    # Filename might already be in meta (from SQLite JOIN)
    filename = meta.get("filename")
    if not filename:
        filename = get_pdf_filename(doc_id) or _default_filename(doc_id)
    
    if filename:
        meta.setdefault("filename", filename)
        meta.setdefault("rel_path", filename)

    # source_url might be in meta
    # If not, we could look it up, but usually it's passed through
    
    page = _coerce_page(meta.get("page"))
    if page is not None:
        meta["page"] = page

    pdf_url = build_pdf_url(doc_id, page, filename)
    if pdf_url:
        meta["url"] = pdf_url

    return meta
