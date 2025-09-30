"""
/api/ask endpoint: takes a question and returns an answer with source citations.
Thin FastAPI layer over the QAPipeline; all provider choices live in configs/runtime.yaml.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.factory import build_pipeline

router = APIRouter(tags=["ask"])

class AskRequest(BaseModel):
    question: str = Field(..., min_length=5)
    k: int = 6
    temperature: float = 0.2
    max_output_tokens: int = 600

class SourceItem(BaseModel):
    sid: str
    doc_id: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    url: Optional[str] = None
    score: Optional[float] = None
    snippet: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    usage: dict | None = None

@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Empty question.")
    pipe = build_pipeline()
    out = pipe.ask(
        question=req.question,
        k=req.k,
        temperature=req.temperature,
        max_tokens=req.max_output_tokens
    )
    return AskResponse(answer=out["answer"], sources=out["sources"], usage=out.get("usage"))
