from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
import uuid


class LoginRequest(BaseModel):
    """
    What the client sends to POST /auth/login.
    EmailStr validates the email format automatically.
    """
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")
        return v


class TokenResponse(BaseModel):
    """
    What we return after successful login.
    Never include the user's password or role internals here.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    """POST /auth/refresh — exchange a refresh token for a new access token."""
    refresh_token: str


class RegisterUserRequest(BaseModel):
    """
    POST /auth/register — for creating new agent/admin accounts.
    Customers register through a different, simpler flow.

    PASSWORD RULES:
      Min 8 chars enforced here at the schema level.
      The service layer hashes the password before any DB write.
      We never store or log plaintext passwords.
    """
    email: EmailStr
    password: str
    full_name: str
    role_name: str = "agent"  # default role for new registrations

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class UserResponse(BaseModel):
    """
    Safe representation of a user — returned after login or registration.
    hashed_password is intentionally EXCLUDED.
    role is included as a string name, not the internal role_id UUID.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    role_name: Optional[str] = None  # populated from relationship in service