from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---

class UserAIConfigCreate(BaseModel):
    config_name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_id: str = Field(min_length=1, max_length=100)
    service_type: str = Field(min_length=1, max_length=30)
    api_base_url: str | None = None
    api_key: str | None = None  # Plain text, encrypted server-side
    is_enabled: bool = True
    is_default: bool = False
    extra_config: str | None = None  # JSON string


class UserAIConfigUpdate(BaseModel):
    config_name: str | None = Field(None, min_length=1, max_length=100)
    provider: str | None = Field(None, min_length=1, max_length=50)
    model_id: str | None = Field(None, min_length=1, max_length=100)
    service_type: str | None = Field(None, min_length=1, max_length=30)
    api_base_url: str | None = None
    api_key: str | None = None  # If None/empty, keep existing key
    is_enabled: bool | None = None
    is_default: bool | None = None
    extra_config: str | None = None


# --- Responses ---

class UserAIConfigResponse(BaseModel):
    id: int
    user_id: int
    config_name: str
    provider: str
    model_id: str
    service_type: str
    api_base_url: str | None
    api_key_hint: str | None
    is_enabled: bool
    is_default: bool
    extra_config: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class UserAIConfigListResponse(BaseModel):
    items: list[UserAIConfigResponse]
    total: int
