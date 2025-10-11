"""
app/main.py

FastAPI application entrypoint.
- Creates the FastAPI app instance.
- Registers all routers (health, search, ask).
- Adds CORS for local dev (restrict in production).
- Provides a friendly "/" redirect to Swagger docs to avoid confusing 404s.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

# Routers
from app.routers import health, search
from app.routers import ask  # new: /api/ask (Q&A with citations)
from app.routers import pdf

app = FastAPI(
    title="Cotton RAG API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS for local frontend dev; lock this down before you brag to the client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # TODO: replace with your frontend origin(s) in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root: be nice during dev instead of 404ing
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

# Quick ping that doesn’t depend on your routers
@app.get("/api/ping", include_in_schema=False)
def ping():
    return JSONResponse({"status": "ok", "service": "cotton-rag", "version": "0.1.0"})

# Routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(ask.router, prefix="/api", tags=["ask"])
app.include_router(pdf.router)
