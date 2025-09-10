# app/api.py
# Purpose: Defines the FastAPI app and HTTP routes (/health, /search).
# - /health: simple liveness check.
# - /search: minimal retrieval API that returns a stable JSON contract.

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import SearchResponse
from app.service.search_service import search_service

app = FastAPI(title="Cotton Knowledge Hub API", version="0.1.0")

# CORS for local frontend dev; tighten later by domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="User query"),
    k: int = Query(8, ge=1, le=50, description="Number of results")
):
    try:
        return search_service(q=q, k=k)
    except Exception as e:
        # Don’t leak stack traces; bubble up a concise message
        raise HTTPException(status_code=500, detail=str(e))
