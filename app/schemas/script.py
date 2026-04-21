import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# --- Requests ---

class CreateScriptRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    theme: str | None = None
    sub_theme: str | None = None
    duration_seconds: int | None = None
    narrative_type: str | None = None
    content: str
    viral_elements: dict | list | str | None = None
    source_case_id: int | None = None


class UpdateScriptRequest(BaseModel):
    title: str | None = None
    theme: str | None = None
    sub_theme: str | None = None
    duration_seconds: int | None = None
    narrative_type: str | None = None
    content: str | None = None
    viral_elements: dict | list | str | None = None


class GenerateScriptRequest(BaseModel):
    """AI 脚本生成请求"""
    title: str = Field(min_length=1, max_length=200)
    theme: str | None = None
    sub_theme: str | None = None
    duration_seconds: int | None = Field(default=60, description="目标时长（秒）")
    narrative_type: str | None = Field(default=None, description="叙事类型，如：悬念、温情、搞笑、反转")
    source_case_id: int | None = Field(default=None, description="参考知识库案例 ID")
    video_style: str | None = Field(default="cinematic", description="视频风格：cinematic/anime/animation/cyberpunk/oil_painting")
    custom_prompt: str | None = Field(default=None, description="额外要求，如：角色设定、场景要求等")


class ViralCheckRequest(BaseModel):
    content: str


# --- Responses ---

class ScriptResponse(BaseModel):
    id: int
    title: str
    theme: str | None
    sub_theme: str | None
    duration_seconds: int | None
    narrative_type: str | None
    content: str
    viral_elements: dict | list | str | None
    source_case_id: int | None
    script_path: str | None = None
    version: int
    is_current: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("viral_elements", mode="before")
    @classmethod
    def parse_viral_elements(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v
