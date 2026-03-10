from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine — the core connection manager
# pool_pre_ping: validates connections are alive before using them
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,        # Connections kept open in the pool
    max_overflow=20,     # Extra connections allowed under load
    echo=settings.app_debug,  # Log SQL queries in debug mode only
)

# ---------------------------------------------------------------------------
# Session factory — autocommit=False means we control transactions explicitly
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# Base class for all ORM models
# All models inherit from this — SQLAlchemy uses it to track table mappings
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session per request
# ---------------------------------------------------------------------------
def get_db():
    """
    Dependency that provides a database session for the duration of a request.

    Usage in a route:
        @router.get("/tickets")
        def list_tickets(db: Session = Depends(get_db)):
            ...

    The 'finally' block ensures the session is always closed,
    even if an unhandled exception occurs mid-request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()