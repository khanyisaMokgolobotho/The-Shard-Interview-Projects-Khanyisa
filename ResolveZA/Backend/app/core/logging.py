import logging
import structlog
from app.core.config import get_settings


def configure_logging() -> None:
    """
    Sets up structlog with JSON output in production, pretty output in dev.
    Called once at application startup in main.py.
    """
    settings = get_settings()
    is_production = settings.app_env == "production"

    # Configure standard library logging (used by uvicorn, sqlalchemy)
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if settings.app_debug else logging.INFO,
    )

    # Shared processors — applied to every log line
    shared_processors = [
        structlog.contextvars.merge_contextvars,       # Request-scoped context
        structlog.stdlib.add_log_level,                # "level": "info"
        structlog.stdlib.add_logger_name,              # "logger": "app.api.tickets"
        structlog.processors.TimeStamper(fmt="iso"),   # "timestamp": "2024-..."
        structlog.processors.StackInfoRenderer(),
    ]

    if is_production:
        # JSON output for log aggregation pipelines
        renderer = structlog.processors.JSONRenderer()
    else:
        # Colourful human-readable output for local dev
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Returns a named structured logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("ticket_created", ticket_id=ticket.id, user_id=user.id)
    """
    return structlog.get_logger(name)