# app/routers/search.py
# # Purpose: # Defines the /api/search endpoint for the Cotton RAG API. 
# # - Accepts user queries and retrieval parameters (q, k, neighbors, per_doc).
# # - Delegates search logic to SearchService. 
# # - Returns results in a typed schema consistent with API_CONTRACT.md.

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.schemas import SearchResponse
from app.service.search_service import search_service  # <- function, not class

router = APIRouter(tags=["search"])

@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Query text"),
    k: int = Query(8, ge=1, le=50, description="Top-k results"),
    neighbors: int = Query(2, ge=0, le=10, description="Chunks to stitch before/after hit"),
    per_doc: int = Query(2, ge=1, le=10, alias="per-doc", description="Max results per document"),
    contains: Optional[str] = Query(None, description="Comma-separated keywords that must appear"),
    year: Optional[str] = Query(None, description="Year or range, e.g. 2021 or 2018-2024"),
    cursor: Optional[str] = Query(None, description="Pagination token (reserved)"),
):
    try:
        year_min = year_max = None
        if year:
            if "-" in year:
                a, b = year.split("-", 1)
                year_min, year_max = int(a), int(b)
            else:
                year_min = year_max = int(year)

        # Pass through what the CLI actually supports
        return search_service(
            q=q,
            k=k,
            neighbors=neighbors,
            per_doc=per_doc,
            contains=contains,
            year_min=year_min,
            year_max=year_max,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
