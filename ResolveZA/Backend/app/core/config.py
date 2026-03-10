"""
app/core/config.py

Centralised application configuration using Pydantic Settings.

WHY THIS EXISTS:
  - All config comes from environment variables (12-factor app principle)
  - Pydantic validates types at startup — bad config crashes early, not mid-request
  - One place to change settings, no scattered os.getenv() calls
  - Secrets never hardcoded — satisfies OWASP A02 (Cryptographic Failures)

POPIA NOTE:
  Connection strings, JWT secrets, and passwords are never logged.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = "ResolveZA"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = False

    # -------------------------------------------------------------------------
    # Database (SQL Server)
    # We build the connection string here so no other file touches raw creds
    # -------------------------------------------------------------------------
    db_host: str = "db"
    db_port: int = 1433
    db_name: str = "resolveza"
    db_user: str = "sa"
    db_sa_password: str

    @property
    def database_url(self) -> str:
        """
        Returns SQLAlchemy-compatible connection string for SQL Server.
        Uses ODBC Driver 18 — the current Microsoft recommendation.
        TrustServerCertificate=yes for local dev; remove in production.
        """
        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_sa_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?driver=ODBC+Driver+18+for+SQL+Server"
            f"&TrustServerCertificate=yes"
        )

    # -------------------------------------------------------------------------
    # JWT Authentication
    # -------------------------------------------------------------------------
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # -------------------------------------------------------------------------
    # Redis / Celery
    # -------------------------------------------------------------------------
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    allowed_origins: list[str] = ["http://localhost:3000"]

    # -------------------------------------------------------------------------
    # Pydantic Settings: read from .env file automatically
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    lru_cache means the .env file is only read once per process — efficient.
    Use dependency injection in FastAPI routes: Depends(get_settings)
    """
    return Settings()

# Convenience aliases used by auth_service.py
Settings.access_token_expire_minutes = property(lambda self: self.jwt_access_token_expire_minutes)
Settings.refresh_token_expire_days = property(lambda self: self.jwt_refresh_token_expire_days)