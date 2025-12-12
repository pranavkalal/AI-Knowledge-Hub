"""
/api/ask endpoint: takes a question and returns an answer with source citations.
Thin FastAPI layer over the QAPipeline or LangChain chain via app.factory.build_pipeline.
All provider choices live in configs/runtime/default.yaml (or the preset referenced by COTTON_RUNTIME).
"""

from time import perf_counter
from typing import Optional, List
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, AliasChoices

from app.factory import build_pipeline

router = APIRouter(tags=["ask"])

# --------- Request / Response Models ---------
class AskFilters(BaseModel):
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    # add other keys your store supports (contains, neighbors, per_doc) if needed
    contains: Optional[str] = None
    neighbors: Optional[int] = None
    per_doc: Optional[int] = None
    max_preview_chars: Optional[int] = None
    max_snippet_chars: Optional[int] = None
    diversify_per_doc: Optional[bool] = None

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
    sid: Optional[str] = None
    doc_id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None      # some docs have 'name' separate to 'title'
    year: Optional[int] = None
    page: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x, y, width, height] for deep linking
    span: Optional[str] = None      # mapped from pipeline "snippet"
    score: Optional[float] = None   # original retrieval score
    cosine: Optional[float] = None  # alias (when vectors are L2-normalized)
    faiss_score: Optional[float] = None
    rerank_score: Optional[float] = None
    url: Optional[str] = None
    source_url: Optional[str] = None
    rel_path: Optional[str] = None
    filename: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    # Back-compat: some clients still expect "sources" -> mirror citations
    sources: Optional[List[Citation]] = None
    usage: Optional[dict] = None
    latency_ms: Optional[int] = None

# --------- Route ---------
def _run_pipeline(req: AskRequest) -> AskResponse:
    q = (req.question or "").strip()
    if len(q) < 5:
        raise HTTPException(status_code=400, detail="Question too short.")

    t0 = perf_counter()
    pipe = build_pipeline()

    kwargs = dict(
        question=q,
        k=req.k,
        temperature=req.temperature,
        max_tokens=req.max_output_tokens,
    )
    if req.filters is not None:
        kwargs["filters"] = req.filters.model_dump(exclude_none=True)
    if req.mode is not None:
        kwargs["mode"] = req.mode
    if req.rerank is not None:
        kwargs["rerank"] = bool(req.rerank)

    try:
        out = pipe.ask(**kwargs)  # expected keys: "answer", "sources", optional "usage"
    except Exception as e:
        # Log server-side for debugging; keep response clean
        # You can swap print for proper logging if you added it.
        print("[/api/ask] pipeline error:", repr(e))
        raise HTTPException(status_code=500, detail=f"ask pipeline failed: {type(e).__name__}")

    answer = out.get("answer") or ""
    raw_sources = out.get("sources") or []

    def _coerce_page(value):
        if isinstance(value, list) and value:
            value = value[0]
        if value in (None, "", []):
            return None
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return None

    citations: List[Citation] = []
    for s in raw_sources:
        page_val = _coerce_page(s.get("page"))
        rel_path = s.get("rel_path") or s.get("filename")
        
        # Extract bbox if available (for deep linking)
        # Extract bbox if available (for deep linking)
        # DB stores 'bboxes' (list of dicts with 'polygon'), we want 'bbox' [x, y, w, h]
        bbox = s.get("bbox")
        bboxes = s.get("bboxes")
        
        if not bbox and bboxes and isinstance(bboxes, list) and len(bboxes) > 0:
            # Take the first bbox as a fallback/default highlight
            first_bbox = bboxes[0]
            if isinstance(first_bbox, dict) and "polygon" in first_bbox:
                poly = first_bbox["polygon"]
                if isinstance(poly, list) and len(poly) >= 8:
                    # Convert 8-point polygon to [x, y, w, h]
                    xs = poly[0::2]
                    ys = poly[1::2]
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)
                    bbox = [min_x, min_y, max_x - min_x, max_y - min_y]

        if bbox and isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            # Ensure all values are floats
            try:
                bbox = [float(x) for x in bbox]
            except (TypeError, ValueError):
                bbox = None
        else:
            bbox = None
        
        citations.append(
            Citation(
                sid=s.get("sid"),
                doc_id=s.get("doc_id"),
                title=s.get("title"),
                name=s.get("name"),
                year=s.get("year"),
                page=page_val,
                bbox=bbox,  # Add bbox for deep linking
                url=s.get("url"),
                source_url=s.get("source_url"),
                rel_path=rel_path,
                filename=s.get("filename") or rel_path,
                score=s.get("score"),
                faiss_score=s.get("faiss_score"),
                rerank_score=s.get("rerank_score"),
                cosine=s.get("cosine") or s.get("faiss_score") or s.get("score"),
                span=s.get("snippet") or s.get("span") or s.get("preview"),
            )
        )
        
        # Construct local URL if missing
        if not citations[-1].url and (citations[-1].filename or citations[-1].rel_path):
            fname = citations[-1].filename or citations[-1].rel_path
            # Use the filename endpoint
            citations[-1].url = f"/api/pdf/{fname}"

    latency_ms = int((perf_counter() - t0) * 1000)
    return AskResponse(
        answer=answer,
        citations=citations,
        sources=citations,  # back-compat mirror
        usage=out.get("usage"),
        latency_ms=latency_ms,
    )

# Accept both /ask and /ask/ to avoid 405s from sloppy URLs
@router.post("/ask", response_model=AskResponse, response_model_exclude_none=True)
async def ask_post(req: AskRequest, stream: bool = Query(False)):
    if not stream:
        return _run_pipeline(req)

    question = (req.question or "").strip()
    if len(question) < 5:
        raise HTTPException(status_code=400, detail="Question too short.")

    pipe = build_pipeline()
    if not hasattr(pipe, "stream"):
        raise HTTPException(status_code=400, detail="Streaming not supported by current orchestrator.")

    stream_kwargs = {
        "k": req.k,
    }
    if req.filters is not None:
        stream_kwargs["filters"] = req.filters.model_dump(exclude_none=True)
    if req.mode is not None:
        stream_kwargs["mode"] = req.mode
    if req.rerank is not None:
        stream_kwargs["rerank"] = bool(req.rerank)

    async def event_generator():
        try:
            async for chunk in pipe.stream(question=question, temperature=req.temperature, max_tokens=req.max_output_tokens, **stream_kwargs):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            print("[/api/ask] stream error:", repr(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/ask/", response_model=AskResponse, response_model_exclude_none=True)
async def ask_post_slash(req: AskRequest, stream: bool = Query(False)):
    return await ask_post(req, stream=stream)
