"""
Serve local PDF documents for citation links.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from rag.retrieval.pdf_links import get_pdf_filename, PDF_ROOT

router = APIRouter(tags=["pdf"])


def _resolve_path(filename: str) -> Path:
    safe_name = Path(filename).name
    candidate = (PDF_ROOT / safe_name).resolve()
    try:
        candidate.relative_to(PDF_ROOT)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    if candidate.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Unsupported file type")
    return candidate


@router.get("/pdf/{filename}")
def pdf_by_filename(filename: str):
    path = _resolve_path(filename)
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get("/pdf/by-id/{doc_id}")
def pdf_by_doc_id(doc_id: str):
    filename = get_pdf_filename(doc_id)
    if not filename:
        raise HTTPException(status_code=404, detail="PDF not found for doc_id")
    path = _resolve_path(filename)
    return FileResponse(path, media_type="application/pdf", filename=path.name)
