"""
app/main.py

FastAPI application entrypoint.
- Creates the FastAPI app instance.
- Registers all routers (health, ask, pdf).
- Adds CORS middleware with configurable origins.
- Adds rate limiting to protect against abuse.
- Adds security headers middleware.
- Adds optional API key authentication.
- Provides a friendly "/" redirect to Swagger docs to avoid confusing 404s.
"""

import os
import logging

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Routers
from app.routers import health
from app.routers import ask  # /api/ask (Q&A with citations)
from app.routers import pdf
from app.routers import library  # /api/library (document browsing)
from app.routers import feedback  # /api/feedback (user ratings)

logger = logging.getLogger(__name__)

# --- Environment Detection ---
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "").lower() == "production"

# --- API Key Authentication ---
API_KEY = os.environ.get("API_KEY")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """
    Verify API key if API_KEY environment variable is set.
    In development (no API_KEY set), authentication is skipped.
    """
    if not API_KEY:
        # No API key configured - skip authentication (dev mode)
        return None
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Prevent caching of sensitive data
        if "/api/" in request.url.path:
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

# --- Rate Limiter Setup ---
# Default: 30 requests/minute per IP. Override via RATE_LIMIT env var.
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

# --- FastAPI App Configuration ---
# Disable Swagger/OpenAPI docs in production for security
app = FastAPI(
    title="AI Knowledge Hub API",
    version="0.1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    # Add global API key dependency for all routes when API_KEY is set
    dependencies=[Depends(verify_api_key)] if API_KEY else [],
)

# Attach limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Security Headers Middleware ---
app.add_middleware(SecurityHeadersMiddleware)

# --- CORS Configuration ---
# For production, set CORS_ORIGINS env var to comma-separated list of allowed origins
# e.g., CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
# Defaults to permissive for local development
_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_env:
    ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
elif IS_PRODUCTION:
    # Fail secure: require explicit CORS configuration in production
    logger.warning("CORS_ORIGINS not set in production - using restrictive defaults")
    ALLOWED_ORIGINS = []  # No origins allowed - must be explicitly configured
else:
    # Development defaults
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Log configuration on startup
@app.on_event("startup")
async def log_startup_config():
    logger.info("=" * 60)
    logger.info("AI Knowledge Hub API Starting")
    logger.info("=" * 60)
    logger.info("Environment: %s", "PRODUCTION" if IS_PRODUCTION else "DEVELOPMENT")
    logger.info("API Key Auth: %s", "ENABLED" if API_KEY else "DISABLED (set API_KEY to enable)")
    logger.info("Swagger/Docs: %s", "DISABLED" if IS_PRODUCTION else "ENABLED at /docs")
    logger.info("CORS allowed origins: %s", ALLOWED_ORIGINS if ALLOWED_ORIGINS else "(none - all blocked)")
    logger.info("Security headers: ENABLED")
    
    # Initialize LangSmith tracing if API key is configured
    langsmith_key = os.environ.get("LANGSMITH_API_KEY")
    if langsmith_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        project = os.environ.get("LANGCHAIN_PROJECT", "crdc-knowledge-hub")
        logger.info("LangSmith tracing: ENABLED for project '%s'", project)
    else:
        logger.info("LangSmith tracing: DISABLED")
    logger.info("=" * 60)



# Root: be nice during dev instead of 404ing
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# Quick ping that doesn't depend on your routers
@app.get("/api/ping", include_in_schema=False)
def ping():
    return JSONResponse({"status": "ok", "service": "ai-knowledge-hub", "version": "0.1.0"})


# Routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(ask.router, prefix="/api", tags=["ask"])
app.include_router(pdf.router)
app.include_router(library.router, prefix="/api", tags=["library"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
