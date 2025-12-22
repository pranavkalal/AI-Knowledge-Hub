"""
/api/ask endpoint: Blueprint Definition.

This file defines the API contract for the Question Answering endpoint.
Usage: POST /api/ask with { "question": "..." }
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, AliasChoices

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])

# --------- Request / Response Models ---------
# These Pydantic models demonstrate robust type validation and documentation.

class AskFilters(BaseModel):
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    contains: Optional[str] = None
    neighbors: Optional[int] = None
    per_doc: Optional[int] = None
    max_preview_chars: Optional[int] = None
    max_snippet_chars: Optional[int] = None
    diversify_per_doc: Optional[bool] = None


class AskRequest(BaseModel):
    # Accept BOTH "question" and "query" in the payload; standardize on "question"
    question: str = Field(
        ..., 
        min_length=5, 
        max_length=2000,
        validation_alias=AliasChoices("question", "query")
    )
    k: int = Field(6, ge=1, le=50)
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    max_output_tokens: int = Field(600, ge=64, le=4096)
    mode: Optional[str] = Field(default="dense")
    rerank: Optional[bool] = False
    filters: Optional[AskFilters] = None
    persona: Optional[str] = Field(default="grower")


class Citation(BaseModel):
    """Standardized Citation Object"""
    sid: Optional[str] = None
    doc_id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    year: Optional[int] = None
    page: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x, y, width, height] for deep linking
    span: Optional[str] = None
    score: Optional[float] = None
    url: Optional[str] = None
    rel_path: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    usage: Optional[dict] = None
    latency_ms: Optional[int] = None


# --------- Blueprint Route ---------

@router.post("/ask", response_model=AskResponse)
async def ask_post(request: Request, req: AskRequest, stream: bool = Query(False)):
    """
    Blueprint Endpoint: Simulates the Q&A pipeline entry point.
    
    In the live system, this connects to the LangGraph orchestration layer.
    For this portfolio reference, the implementation is hidden.
    """
    logger.info("Blueprint endpoint accessed: /ask")
    
    # Simulation of what would happen:
    # 1. Validation (Pydantic handles this)
    # 2. Pipeline Instantiation (cached)
    # 3. Async Execution (Streaming or unary)
    
    raise HTTPException(
        status_code=501, 
        detail="This is a blueprint/portfolio version. The active inference engine is not deployed here."
    )
