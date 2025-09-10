# app/schemas.py
# Purpose: Pydantic models for the /search API response to keep the JSON contract stable.

from typing import List, Optional
from pydantic import BaseModel

class SearchResult(BaseModel):
    doc_id: str
    chunk_id: int
    score: float
    title: Optional[str] = None
    year: Optional[int] = None
    preview: str
    neighbor_window: Optional[List[int]] = None
    source_url: Optional[str] = None
    filename: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    params: dict
    count: int
    results: List[SearchResult]
