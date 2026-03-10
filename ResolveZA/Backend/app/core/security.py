from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing — use a pure-Python scheme to avoid bcrypt backend issues
# in the local Python 3.12 test environment.
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
dummy_password_hash = pwd_context.hash("resolveza-dummy-password")


def hash_password(password: str) -> str:
    """Hash a plaintext password. Call this before any DB write."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare plaintext password against stored hash.
    Returns True if they match, False otherwise.
    NEVER compare passwords with ==. Always use this function.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT token operations
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, role: str) -> str:
    """
    Create a short-lived access token (30 min).
    Payload (claims):
      sub  = subject (user ID)
      role = user's role name (for RBAC checks without DB lookup)
      type = "access" (to distinguish from refresh tokens)
      exp  = expiry timestamp
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived refresh token (7 days).
    Does NOT include role — role may change; refresh tokens are just for re-auth.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT. Raises HTTPException on any failure.

    Failures caught:
      - Invalid signature (tampered token)
      - Expired token
      - Malformed token
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependencies — inject authenticated user into routes
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: decode the Bearer token and return the User object.

    Usage in a route:
        @router.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user

    Raises 401 if:
      - No token provided
      - Token is invalid or expired
      - Token type is not "access"
      - User no longer exists or is disabled
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    # Reject refresh tokens used as access tokens
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # JWT stores user_id as a string — convert back to UUID for the ORM filter.
    # SQLAlchemy's Uuid() type expects a uuid.UUID object on SQLite.
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account disabled",
        )

    return user


def require_roles(*allowed_roles: str):
    """
    RBAC factory — returns a FastAPI dependency that enforces role access.

    Usage:
        @router.patch("/refunds/{id}/approve")
        def approve_refund(
            current_user: User = Depends(require_roles("supervisor", "admin"))
        ):

    This is a "dependency factory" — a function that returns a dependency.
    We need this pattern because FastAPI dependencies can't accept arguments
    directly, but factory functions can.
    """
    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return _check_role
