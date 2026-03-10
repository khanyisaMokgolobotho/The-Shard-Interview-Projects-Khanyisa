import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app as fastapi_app
from app.core.middleware import MAX_REQUEST_SIZE_BYTES, DANGEROUS_CHARS_PATTERN


# ─── Security Headers ─────────────────────────────────────────────────────────

class TestSecurityHeaders:
    """Every response should include our security headers."""

    def test_x_content_type_options(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_xss_protection(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert resp.headers.get("x-xss-protection") == "1; mode=block"

    def test_referrer_policy(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert "camera=()" in resp.headers.get("permissions-policy", "")

    def test_content_security_policy(self):
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_not_set_in_development(self):
        """HSTS should only be set in production — never in dev."""
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        # In test env (APP_ENV=development), HSTS should not be present
        assert "strict-transport-security" not in resp.headers

    def test_server_header_removed(self):
        """Don't leak server software info."""
        client = TestClient(fastapi_app)
        resp = client.get("/health")
        assert "server" not in resp.headers or resp.headers.get("server") == ""


# ─── Request Size Limiting ────────────────────────────────────────────────────

class TestRequestSizeLimit:

    def test_normal_request_passes(self):
        """A request under 1MB should not be rejected with 413."""
        client = TestClient(fastapi_app, raise_server_exceptions=False)
        resp = client.post(
            "/auth/login",
            json={"email": "test@test.com", "password": "Password123!"},
            headers={"Content-Length": "50"},
        )
        # Should be rejected by auth/DB, NOT by size limiting
        assert resp.status_code != 413

    def test_oversized_request_rejected(self):
        """A request claiming to be over 1MB is rejected with 413."""
        client = TestClient(fastapi_app)
        resp = client.post(
            "/auth/login",
            json={"email": "test@test.com"},
            headers={"Content-Length": str(MAX_REQUEST_SIZE_BYTES + 1)},
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()

    def test_413_response_has_detail(self):
        """413 response should include a helpful message."""
        client = TestClient(fastapi_app)
        resp = client.post(
            "/customers",
            json={},
            headers={"Content-Length": str(MAX_REQUEST_SIZE_BYTES + 100)},
        )
        assert resp.status_code == 413
        data = resp.json()
        assert "detail" in data


# ─── Input Sanitization ───────────────────────────────────────────────────────

class TestInputSanitization:
    """Null bytes and control characters should be stripped from input."""

    def test_dangerous_chars_pattern_matches_null_byte(self):
        """The regex should match null bytes."""
        assert DANGEROUS_CHARS_PATTERN.search("\x00") is not None

    def test_dangerous_chars_pattern_matches_control_chars(self):
        """Control characters \x01-\x08 should be matched."""
        for char in "\x01\x02\x03\x04\x05\x06\x07\x08":
            assert DANGEROUS_CHARS_PATTERN.search(char) is not None, \
                f"Expected {repr(char)} to be matched"

    def test_dangerous_chars_pattern_allows_normal_text(self):
        """Normal text, tabs, newlines should NOT be matched."""
        safe = "Hello, World! \t\n\r 123 àéü"
        assert DANGEROUS_CHARS_PATTERN.search(safe) is None

    def test_sanitization_strips_null_bytes(self):
        """
        A request body containing null bytes should be sanitized.
        The route may still fail (e.g. auth failure), but not with a
        payload containing null bytes.
        """
        from app.core.middleware import InputSanitizationMiddleware
        middleware = InputSanitizationMiddleware(app=None)

        dirty = '{"email": "test\x00@test.com", "password": "pass"}'
        clean = middleware._sanitize_string(dirty)
        assert "\x00" not in clean
        assert "test@test.com" in clean

    def test_sanitization_preserves_unicode(self):
        """Unicode characters like Zulu names should be preserved."""
        from app.core.middleware import InputSanitizationMiddleware
        middleware = InputSanitizationMiddleware(app=None)

        text = '{"name": "Nomsa Dlamini-Zulu"}'
        result = middleware._sanitize_string(text)
        assert result == text  # no change

    def test_sanitization_preserves_json_structure(self):
        """Sanitization should not break valid JSON syntax."""
        import json
        from app.core.middleware import InputSanitizationMiddleware
        middleware = InputSanitizationMiddleware(app=None)

        original = '{"subject": "Billing\x00Issue", "priority": "HIGH"}'
        sanitized = middleware._sanitize_string(original)
        # Should still be valid JSON after sanitization
        parsed = json.loads(sanitized)
        assert parsed["priority"] == "HIGH"
        assert "\x00" not in parsed["subject"]


# ─── Rate Limiting ────────────────────────────────────────────────────────────

class TestRateLimiting:
    """Rate limiting should kick in after too many requests."""

    def test_rate_limit_config_exists(self):
        """The limiter should be attached to the app state."""
        assert hasattr(fastapi_app.state, "limiter")

    def test_login_rate_limit_triggers_429(self, integration_db):
        """
        Hitting /auth/login 11 times in a row should result in a 429.
        The rate limit is 10/minute, so the 11th request should be blocked.
        """
        from app.db.session import get_db

        def override_get_db():
            yield integration_db

        fastapi_app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            responses = []
            for _ in range(12):
                resp = client.post(
                    "/auth/login",
                    json={"email": "nobody@test.com", "password": "wrong"},
                )
                responses.append(resp.status_code)

            # Should get 401s (bad credentials) then 429 (rate limited)
            # 401 means the request reached the route — rate limiter is counting
            assert 429 in responses, (
                f"Expected 429 in responses after 12 attempts, got: {set(responses)}"
            )
        finally:
            fastapi_app.dependency_overrides.clear()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def integration_db():
    """Minimal in-memory DB for rate limit test."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.session import Base
    import app.models  # noqa

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
    yield session
    session.close()
    Base.metadata.drop_all(engine)