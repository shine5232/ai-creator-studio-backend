from datetime import datetime

from pydantic import BaseModel, Field, field_validator


SUPPORTED_PLATFORMS = {"youtube", "douyin", "bilibili"}


# --- Requests ---

class AddSocialAccountRequest(BaseModel):
    platform: str = Field(min_length=1)
    account_name: str = Field(min_length=1)
    account_id: str | None = None
    auth_data: dict | None = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform '{v}'. Must be one of: {', '.join(sorted(SUPPORTED_PLATFORMS))}")
        return v


class PublishRequest(BaseModel):
    account_id: int
    asset_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    tags: list[str] | None = None


# --- Responses ---

class SocialAccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    account_id: str | None
    is_active: bool
    last_publish_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class PublishRecordResponse(BaseModel):
    id: int
    project_id: int
    account_id: int
    asset_id: int | None
    title: str
    description: str | None
    tags: list[str] | None
    platform_post_id: str | None
    platform_url: str | None
    status: str
    published_at: datetime | None
    error_message: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class PublishStatusResponse(BaseModel):
    record_id: int
    status: str
    platform_post_id: str | None = None
    platform_url: str | None = None
    error_message: str | None = None
    published_at: str | None = None
    progress: int | None = None
    step_status: str | None = None
    step_error: str | None = None
