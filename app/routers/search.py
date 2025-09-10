from fastapi import APIRouter, Query
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
