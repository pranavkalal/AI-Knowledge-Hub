"""
app/main.py

FastAPI application entrypoint.
- Creates the FastAPI app instance.
- Registers all routers (search, health, etc.).
- Adds middleware (e.g., CORS).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search, health

app = FastAPI(title="Cotton RAG API", version="0.1.0")

# CORS for local frontend dev; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api")
app.include_router(search.router, prefix="/api")
