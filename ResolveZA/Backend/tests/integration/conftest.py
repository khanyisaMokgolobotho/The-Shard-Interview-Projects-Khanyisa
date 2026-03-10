import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.session import Base, get_db
import app.models  # noqa — registers all models


@pytest.fixture(scope="function")
def db():
    """
    Fresh SQLite in-memory DB for each integration test.
    Shared via StaticPool so TestClient requests see seeded data.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Override FastAPI's DB dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass  # don't close — we control the session lifecycle

    fastapi_app.dependency_overrides[get_db] = override_get_db

    yield session

    # Cleanup
    fastapi_app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(db):
    """
    TestClient that uses the overridden DB session.
    The `db` fixture must come first to set up the override.
    """
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c