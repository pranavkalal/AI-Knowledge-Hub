"""
Helpers for mapping retrieval metadata to local PDF files.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


PDF_ROOT = Path(os.environ.get("PDF_ROOT", "data/raw")).resolve()
DOCS_META_PATH = Path(os.environ.get("DOCS_META_PATH", "data/staging/docs.jsonl")).resolve()


@lru_cache(maxsize=1)
def _doc_lookup() -> Dict[str, Dict[str, Any]]:
    """Load doc-level metadata (filename, source_url, etc.) keyed by doc_id."""
    mapping: Dict[str, Dict[str, Any]] = {}
    if not DOCS_META_PATH.exists():
        return mapping

    with DOCS_META_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc_id = record.get("id")
            if not doc_id:
                continue
            mapping[str(doc_id)] = {
                "filename": record.get("filename"),
                "source_url": record.get("source_url"),
            }
    return mapping


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

    lookup = _doc_lookup()
    candidates = [doc_id]
    if " " in doc_id:
        candidates.append(doc_id.replace(" ", "%20"))
    if "%20" in doc_id:
        candidates.append(doc_id.replace("%20", " "))

    for key in candidates:
        info = lookup.get(key)
        if info:
            filename = info.get("filename")
            if filename:
                return filename
            break

    for key in candidates:
        filename = _default_filename(key)
        if filename:
            return filename

    return None


def build_pdf_url(doc_id: str, page: Optional[int] = None) -> Optional[str]:
    """Construct the served PDF URL for a document id."""
    if not doc_id:
        return None
    filename = get_pdf_filename(doc_id)
    if not filename:
        return None
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

    info = _doc_lookup().get(doc_id, {})

    filename = meta.get("filename") or info.get("filename") or _default_filename(doc_id)
    if filename:
        meta.setdefault("filename", filename)
        meta.setdefault("rel_path", filename)

    source_url = meta.get("source_url") or info.get("source_url")
    if source_url:
        meta["source_url"] = source_url

    page = _coerce_page(meta.get("page"))
    if page is not None:
        meta["page"] = page

    pdf_url = build_pdf_url(doc_id, page)
    if pdf_url:
        meta["url"] = pdf_url

    return meta
