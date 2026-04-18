from datetime import datetime
from json import loads as json_loads

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Requests ---

class AnalyzeVideoRequest(BaseModel):
    source_url: str
    platform: str = "youtube"


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(min_length=1)
    element_type: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class RecommendThemesRequest(BaseModel):
    description: str | None = None
    platform: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


# --- Responses ---

class KBCaseResponse(BaseModel):
    id: int
    platform: str
    title: str
    source_url: str | None
    uploader: str | None
    upload_date: str | None
    view_count: int | None
    like_count: int | None
    like_rate: float | None
    duration_seconds: int | None
    theme: str | None
    narrative_type: str | None
    story_summary: str | None
    emotion_curve: str | None
    visual_style: str | None
    viral_elements: list | None
    visual_symbols: list | None
    title_formula: str | None
    characters_ethnicity: str | None
    analysis_status: str | None
    frames_dir: str | None
    thumbnail_url: str | None = None
    created_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("viral_elements", "visual_symbols", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                return json_loads(v)
            except (ValueError, TypeError):
                return []
        return v

    @model_validator(mode="after")
    def compute_thumbnail(self):
        if self.frames_dir:
            from pathlib import Path
            thumb = Path(self.frames_dir) / "frame_002.jpg"
            if thumb.exists():
                self.thumbnail_url = f"/api/v1/kb/cases/{self.id}/thumbnail"
        return self


class KBElementResponse(BaseModel):
    id: int
    element_type: str
    name: str
    description: str | None
    impact_score: float | None

    model_config = {"from_attributes": True}


class KBFrameworkResponse(BaseModel):
    id: int
    framework_type: str
    name: str
    description: str | None
    formula: str
    impact_data: dict | None

    model_config = {"from_attributes": True}


class KBScriptTemplateResponse(BaseModel):
    id: int
    name: str
    theme: str | None
    narrative_type: str | None
    duration_seconds: int | None
    template_content: dict | None
    usage_count: int
    created_at: datetime | None

    model_config = {"from_attributes": True}


class KBReferenceContext(BaseModel):
    """用于创作流程的知识库参考上下文"""
    case_id: int
    title: str
    theme: str | None
    narrative_type: str | None
    story_summary: str | None
    emotion_curve: str | None
    visual_style: str | None
    viral_elements: list[str]
    visual_symbols: list[str]
    title_formula: str | None
    characters_ethnicity: str | None
    like_rate: float | None
