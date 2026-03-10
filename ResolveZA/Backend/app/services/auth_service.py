import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, Role
from app.schemas.auth import LoginRequest, RegisterUserRequest, TokenResponse, UserResponse
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, decode_token, dummy_password_hash,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    def list_users(self, db: Session) -> list[UserResponse]:
        users = (
            db.query(User)
            .filter(User.is_active == True)
            .order_by(User.full_name.asc())
            .all()
        )

        return [
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                role_name=user.role.name if user.role else None,
            )
            for user in users
        ]

    def login(self, db: Session, request: LoginRequest) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.

        Security notes:
          - We always call verify_password even if user not found.
            This prevents timing attacks that could reveal valid emails.
            (If we returned early on "user not found", the response time
             would differ from "wrong password" — attackers could enumerate users.)
          - We update last_login_at after successful auth.
        """
        user = db.query(User).filter(
            User.email == request.email,
            User.is_active == True,
        ).first()

        # Always verify password, even for non-existent users.
        # This prevents timing attacks: an attacker can't tell the difference
        # between "user not found" and "wrong password" based on response time.
        # We use a pre-computed dummy hash to keep the timing constant.
        password_to_check = user.hashed_password if user else dummy_password_hash

        if not verify_password(request.password, password_to_check) or not user:
            logger.warning("login_failed", email=request.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Load the role relationship before creating token
        role_name = user.role.name if user.role else "agent"

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("login_success", user_id=str(user.id), role=role_name)

        return TokenResponse(
            access_token=create_access_token(str(user.id), role_name),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=30 * 60,  # 30 minutes in seconds
        )

    def refresh(self, db: Session, refresh_token: str) -> TokenResponse:
        """
        Exchange a valid refresh token for a new access token.
        Validates the token type is "refresh" before issuing new tokens.
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type — expected refresh token",
            )

        user_id = payload.get("sub")
        try:
            user_uuid = uuid.UUID(user_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        user = db.query(User).filter(
            User.id == user_uuid,
            User.is_active == True,
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or account disabled",
            )

        role_name = user.role.name if user.role else "agent"

        return TokenResponse(
            access_token=create_access_token(str(user.id), role_name),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=30 * 60,
        )

    def register(self, db: Session, request: RegisterUserRequest) -> UserResponse:
        """
        Create a new user account (agents, admins — not customers).
        Validates email uniqueness and hashes the password.
        """
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        role = db.query(Role).filter(Role.name == request.role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{request.role_name}' does not exist",
            )

        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            role_id=role.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info("user_registered", user_id=str(user.id), role=role.name)

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_name=role.name,
        )


auth_service = AuthService()
