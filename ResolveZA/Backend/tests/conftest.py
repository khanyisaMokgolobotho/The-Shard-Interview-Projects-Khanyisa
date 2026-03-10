import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.db.session import Base
import app.models  # noqa — registers all models on Base.metadata


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provides a clean SQLite in-memory database session for each test.

    The session is wrapped in a transaction that is ROLLED BACK after
    each test — this is faster than dropping and recreating tables.
    No data persists between tests.
    """
    # SQLite in-memory — fast, no setup required
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # SQLite doesn't enforce foreign keys by default — enable them
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables defined in our models
    Base.metadata.create_all(engine)

    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    yield session

    # Cleanup: rollback any uncommitted changes, close session, drop tables
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()