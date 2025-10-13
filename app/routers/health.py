
# Purpose:
# Defines the /api/health endpoint for the Cotton RAG API.
# - Provides a simple liveness/readiness check.
# - Useful for monitoring and CI/CD deployment probes.
# app/routers/health.py
from fastapi import APIRouter

from app.factory import build_pipeline

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    pipeline = build_pipeline()
    orchestrator = "langchain" if hasattr(pipeline, "stream") else "native"
    return {
        "status": "ok",
        "orchestrator": orchestrator,
        "streaming": bool(getattr(pipeline, "stream", None)),
    }
