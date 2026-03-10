from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    RegisterUserRequest, UserResponse,
)
from app.core.security import get_current_user
from app.models.user import User
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse, summary="Login and get JWT tokens")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email and password.
    Returns access_token (30 min) and refresh_token (7 days).
    """
    return auth_service.login(db, request)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    return auth_service.refresh(db, request.refresh_token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new agent/admin user",
)
def register(request: RegisterUserRequest, db: Session = Depends(get_db)):
    """
    Create a new platform user (agents, admins).
    In production this endpoint should be protected by an admin role.
    """
    return auth_service.register(db, request)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        role_name=current_user.role.name if current_user.role else None,
    )