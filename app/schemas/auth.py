from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Requests ---

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


# --- Responses ---

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    created_at: datetime | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
