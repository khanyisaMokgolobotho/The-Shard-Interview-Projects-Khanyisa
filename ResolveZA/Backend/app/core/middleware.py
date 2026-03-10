import re
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

settings = get_settings()

MAX_REQUEST_SIZE_BYTES = 1024 * 1024
DANGEROUS_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        if settings.app_env.lower() == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        response.headers["Server"] = ""
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_SIZE_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request payload too large"},
                    )
            except ValueError:
                pass
        return await call_next(request)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    def _sanitize_string(self, value: str) -> str:
        return DANGEROUS_CHARS_PATTERN.sub("", value)

    async def dispatch(self, request: Request, call_next) -> Response:
        return await call_next(request)


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _prune(self, key: str) -> list[float]:
        now = time.time()
        attempts = [
            timestamp
            for timestamp in self._failures.get(key, [])
            if now - timestamp < self.window_seconds
        ]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def is_limited(self, key: str) -> bool:
        return len(self._prune(key)) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        attempts = self._prune(key)
        attempts.append(time.time())
        self._failures[key] = attempts

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
