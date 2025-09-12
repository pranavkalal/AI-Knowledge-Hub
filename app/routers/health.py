
# Purpose:
# Defines the /api/health endpoint for the Cotton RAG API.
# - Provides a simple liveness/readiness check.
# - Useful for monitoring and CI/CD deployment probes.
# app/routers/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "ok"}
