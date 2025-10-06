"""
/api/ask endpoint: takes a question and returns an answer with source citations.
Thin FastAPI layer over the QAPipeline; all provider choices live in configs/runtime.yaml.
"""

from time import perf_counter
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, AliasChoices

from app.factory import build_pipeline

router = APIRouter(tags=["ask"])


# --------- Request / Response Models ---------
class AskFilters(BaseModel):
    year_min: Optional[int] = None
    year_max: Optional[int] = None


class AskRequest(BaseModel):
    # Accept BOTH "question" and "query" in the payload; standardize on "question"
    question: str = Field(..., min_length=5, validation_alias=AliasChoices("question", "query"))
    k: int = Field(6, ge=1, le=50)
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    max_output_tokens: int = Field(600, ge=64, le=4096)

    # Optional knobs (pipeline may ignore if unsupported; safe to pass through)
    mode: Optional[str] = Field(default="dense")       # "dense" | "bm25" | "hybrid"
    rerank: Optional[bool] = False
    filters: Optional[AskFilters] = None


class Citation(BaseModel):
    # Unified citation schema used by UI
    doc_id: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    span: Optional[str] = None     # mapped from pipeline "snippet"
    score: Optional[float] = None
    url: Optional[str] = None
    sid: Optional[str] = None      # original source id if provided


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    # Back-compat: some clients still expect "sources" -> mirror citations
    sources: Optional[List[Citation]] = None
    usage: Optional[dict] = None
    latency_ms: Optional[int] = None


# --------- Route ---------
@router.post("/ask", response_model=AskResponse, response_model_exclude_none=True)
def ask(req: AskRequest):
    q = (req.question or "").strip()
    if len(q) < 5:
        raise HTTPException(status_code=400, detail="Question too short.")

    t0 = perf_counter()
    pipe = build_pipeline()

    # Build kwargs conservatively to avoid breaking older pipelines
    kwargs = dict(
        question=q,
        k=req.k,
        temperature=req.temperature,
        max_tokens=req.max_output_tokens,
    )
    # Pass optional knobs only if present; pipeline may no-op them
    if req.filters is not None:
        kwargs["filters"] = req.filters.model_dump(exclude_none=True)
    if req.mode is not None:
        kwargs["mode"] = req.mode
    if req.rerank is not None:
        kwargs["rerank"] = bool(req.rerank)

    try:
        out = pipe.ask(**kwargs)  # expected keys: "answer", "sources", optional "usage"
    except Exception as e:
        # Don't leak stacktraces to the client
        raise HTTPException(status_code=500, detail=f"ask pipeline failed: {type(e).__name__}")

    answer = out.get("answer") or ""
    raw_sources = out.get("sources") or []

    # Normalize pipeline sources -> unified Citation schema
    citations: List[Citation] = []
    for s in raw_sources:
        # tolerate dict-like objects with varied keys
        citations.append(
            Citation(
                sid=s.get("sid"),
                doc_id=s.get("doc_id"),
                title=s.get("title"),
                page=s.get("page"),
                url=s.get("url"),
                score=s.get("score"),
                span=s.get("snippet") or s.get("span") or s.get("preview"),
            )
        )

    latency_ms = int((perf_counter() - t0) * 1000)

    # Mirror into "sources" for back-compat while new UI reads "citations"
    return AskResponse(
        answer=answer,
        citations=citations,
        sources=citations,
        usage=out.get("usage"),
        latency_ms=latency_ms,
    )
