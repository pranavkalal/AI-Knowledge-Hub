"""
Library router - Browse, search.

Serves document metadata from scraped_reports.csv for the Library UI.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(tags=["library"])

# Path to the metadata CSV
CSV_PATH = Path(__file__).parent.parent.parent / "data" / "metadata" / "scraped_reports.csv"
# Path to raw PDFs for the library (different from ingested PDFs)
LIBRARY_PDF_ROOT = Path(__file__).parent.parent.parent / "data" / "raw"


class LibraryDocument(BaseModel):
    """Schema for a library document."""
    title: str
    year: Optional[int] = None
    project_code: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    date_issued: Optional[str] = None
    abstract: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    pdf_url: Optional[str] = None
    source_page: Optional[str] = None
    filename: Optional[str] = None


class LibraryFilters(BaseModel):
    """Available filter options."""
    years: List[int]
    subjects: List[str]
    categories: List[str]


class LibraryResponse(BaseModel):
    """Paginated library response."""
    documents: List[LibraryDocument]
    total: int
    page: int
    limit: int


@lru_cache(maxsize=1)
def _load_documents() -> List[dict]:
    """Load and cache documents from CSV."""
    if not CSV_PATH.exists():
        return []
    
    documents = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse year as int if possible
            year = None
            if row.get("year"):
                try:
                    year = int(row["year"])
                except ValueError:
                    pass
            
            # Build the local PDF URL from filename
            filename = row.get("filename", "")
            local_pdf_url = f"/api/library/pdf/{filename}" if filename else None
            
            documents.append({
                "title": row.get("title", ""),
                "year": year,
                "project_code": row.get("project_code", ""),
                "author": row.get("author", ""),
                "publisher": row.get("publisher", ""),
                "date_issued": row.get("date_issued", ""),
                "abstract": row.get("abstract", ""),
                "category": row.get("category", ""),
                "subject": row.get("subject", ""),
                "pdf_url": local_pdf_url,
                "source_page": row.get("source_page", ""),
                "filename": filename,
            })
    
    return documents


def _filter_documents(
    documents: List[dict],
    query: Optional[str] = None,
    year: Optional[int] = None,
    subject: Optional[str] = None,
    category: Optional[str] = None,
) -> List[dict]:
    """Filter documents based on search criteria."""
    results = documents
    
    # Text search across title, author, abstract
    if query:
        query_lower = query.lower()
        results = [
            doc for doc in results
            if query_lower in (doc.get("title") or "").lower()
            or query_lower in (doc.get("author") or "").lower()
            or query_lower in (doc.get("abstract") or "").lower()
            or query_lower in (doc.get("subject") or "").lower()
        ]
    
    # Year filter
    if year:
        results = [doc for doc in results if doc.get("year") == year]
    
    # Subject filter (partial match)
    if subject:
        subject_lower = subject.lower()
        results = [
            doc for doc in results
            if subject_lower in (doc.get("subject") or "").lower()
        ]
    
    # Category filter
    if category:
        category_lower = category.lower()
        results = [
            doc for doc in results
            if category_lower in (doc.get("category") or "").lower()
        ]
    
    return results


@router.get("/library", response_model=LibraryResponse)
def list_documents(
    q: Optional[str] = Query(None, description="Search query"),
    year: Optional[int] = Query(None, description="Filter by year"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List library documents with optional search and filters.
    
    - **q**: Search text across title, author, abstract, subject
    - **year**: Filter by publication year
    - **subject**: Filter by subject/topic
    - **category**: Filter by report category
    - **page**: Page number (1-indexed)
    - **limit**: Items per page (max 100)
    """
    all_docs = _load_documents()
    filtered = _filter_documents(all_docs, query=q, year=year, subject=subject, category=category)
    
    # Pagination
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    paginated = filtered[start:end]
    
    return LibraryResponse(
        documents=[LibraryDocument(**doc) for doc in paginated],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/library/filters", response_model=LibraryFilters)
def get_filters():
    """
    Get available filter options for the library.
    
    Returns unique years, subjects, and categories from all documents.
    """
    all_docs = _load_documents()
    
    # Extract unique years (sorted descending)
    years = sorted(
        {doc["year"] for doc in all_docs if doc.get("year")},
        reverse=True
    )
    
    # Extract unique subjects (split by comma, cleaned)
    subjects_set = set()
    for doc in all_docs:
        if doc.get("subject"):
            for subj in doc["subject"].split(","):
                subj = subj.strip()
                if subj:
                    subjects_set.add(subj)
    subjects = sorted(subjects_set)
    
    # Extract unique categories
    categories = sorted(
        {doc["category"] for doc in all_docs if doc.get("category")}
    )
    
    return LibraryFilters(
        years=years,
        subjects=subjects,
        categories=categories,
    )


@router.get("/library/pdf/{filename}")
def serve_library_pdf(filename: str):
    """
    Serve a PDF from the library (data/raw directory).
    
    This is separate from the ingested PDFs used for RAG.
    """
    # Security: ensure filename doesn't escape the directory
    safe_name = Path(filename).name
    pdf_path = (LIBRARY_PDF_ROOT / safe_name).resolve()
    
    try:
        pdf_path.relative_to(LIBRARY_PDF_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid path")
    
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    if pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Unsupported file type")
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf", 
        filename=safe_name,
        headers={"Content-Disposition": f"inline; filename={safe_name}"}
    )

