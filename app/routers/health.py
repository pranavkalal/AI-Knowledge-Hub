"""
Health check endpoint for monitoring and deployment probes.
- Provides simple liveness check
- Includes database connectivity check
- Avoids exposing internal architecture details publicly
"""

import os
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Only expose detailed health info in development
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "").lower() == "production"


@router.get("/health")
def health():
    """
    Basic health check for load balancers and monitoring.
    Returns minimal info in production, detailed info in development.
    """
    result = {"status": "ok"}
    
    # Check database connectivity
    try:
        from app.adapters.vector_postgres import PostgresStoreAdapter
        conn_str = os.environ.get("POSTGRES_CONNECTION_STRING")
        if conn_str:
            # Quick connectivity test
            from sqlalchemy import create_engine, text
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["database"] = "connected"
        else:
            result["database"] = "not_configured"
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        result["database"] = "error"
        result["status"] = "degraded"
    
    # Only include internal details in development mode
    if not IS_PRODUCTION:
        try:
            from app.factory import build_pipeline
            pipeline = build_pipeline()
            result["orchestrator"] = "langchain" if hasattr(pipeline, "stream") else "native"
            result["streaming"] = bool(getattr(pipeline, "stream", None))
        except Exception as e:
            logger.warning("Pipeline health check failed: %s", e)
            result["pipeline"] = "error"
    
    return result


@router.get("/health/ready")
def readiness():
    """
    Kubernetes-style readiness probe.
    Returns 200 only if all dependencies are ready.
    """
    errors = []
    
    # Check database
    try:
        conn_str = os.environ.get("POSTGRES_CONNECTION_STRING")
        if conn_str:
            from sqlalchemy import create_engine, text
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        else:
            errors.append("database_not_configured")
    except Exception as e:
        errors.append(f"database_error")
        logger.error("Readiness check - DB error: %s", e)
    
    # Check OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append("openai_key_missing")
    
    if errors:
        return {"status": "not_ready", "errors": errors}
    
    return {"status": "ready"}
