# app/routers/search.py
#
# Purpose:
# Defines the /api/search endpoint for the Cotton RAG API.
# - Accepts user queries and retrieval parameters (q, k, neighbors, per_doc).
# - Delegates search logic to SearchService.
# - Returns results in a typed schema consistent with API_CONTRACT.md.

from fastapi import APIRouter, HTTPException, Query
from app.schemas import SearchResponse
from app.service.search_service import SearchService

router = APIRouter(tags=["search"])
svc = SearchService()

@router.get("/search", response_model=SearchResponse)
def search(q: str = Query(...), k: int = 8, neighbors: int = 2, per_doc: int = 2):
    try:
        return svc.search(q=q, k=k, neighbors=neighbors, per_doc=per_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
