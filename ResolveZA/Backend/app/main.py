from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    InputSanitizationMiddleware,
    LoginRateLimiter,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.tickets import router as tickets_router
from app.api.refunds import router as refunds_router

settings = get_settings()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown logic
# This replaces the deprecated @app.on_event pattern
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    configure_logging()
    logger.info(
        "resolveza_starting",
        environment=settings.app_env,
        version=settings.app_version,
    )
    yield
    # SHUTDOWN
    logger.info("resolveza_stopping")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ResolveZA API",
    description="Telecom dispute resolution platform — AI-assisted Tier-1 support",
    version=settings.app_version,
    docs_url="/docs" if settings.app_debug else None,   # Disable Swagger in prod
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)
app.state.limiter = LoginRateLimiter()

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(InputSanitizationMiddleware)

# ---------------------------------------------------------------------------
# CORS Middleware
# Only allow the frontend origin — not wildcard "*" (OWASP best practice)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------------------------------------------------------------------------
# Routers
# We'll add: /tickets, /customers, /refunds, /auth as we build each feature
# ---------------------------------------------------------------------------
app.include_router(health_router, tags=["observability"])
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(tickets_router)
app.include_router(refunds_router)
