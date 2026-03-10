import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis as redis_client

from app.db.session import get_db
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/health", summary="Liveness check")
def health_live():
    """
    Returns 200 if the application process is running.
    Does NOT check dependencies — that's /health/ready.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/ready", summary="Readiness check — DB + Redis")
def health_ready(db: Session = Depends(get_db)):
    """
    Returns 200 only if ALL dependencies are reachable.
    Returns 503 if any dependency is down.

    Checks:
      - SQL Server: SELECT 1 query
      - Redis: PING command
    """
    start = time.perf_counter()
    checks = {}
    overall_status = "ok"

    # --- Database check ---
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        logger.error("health_db_failed", error=str(e))
        checks["database"] = {"status": "error", "detail": "unreachable"}
        overall_status = "degraded"

    # --- Redis check ---
    try:
        r = redis_client.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        logger.error("health_redis_failed", error=str(e))
        checks["redis"] = {"status": "error", "detail": "unreachable"}
        overall_status = "degraded"

    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response = {
        "status": overall_status,
        "checks": checks,
        "response_time_ms": duration_ms,
    }

    if overall_status != "ok":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=response)

    return response