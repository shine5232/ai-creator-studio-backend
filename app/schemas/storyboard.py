from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---

class CreateStoryboardRequest(BaseModel):
    tone_mapping: dict | None = None


class UpdateStoryboardRequest(BaseModel):
    tone_mapping: dict | None = None


class UpdateShotRequest(BaseModel):
    description: str | None = None
    shot_type: str | None = None
    tone: str | None = None
    mood: str | None = None
    image_prompt: str | None = None
    video_prompt: str | None = None
    video_duration: float | None = None
    video_provider: str | None = None
    video_model: str | None = None


class RegenerateImageRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    image_prompt: str | None = None


class RegenerateVideoRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    video_prompt: str | None = None
    duration: float | None = None


# --- Responses ---

class ShotResponse(BaseModel):
    id: int
    shot_number: int
    act_name: str | None
    time_range: str | None
    shot_type: str | None
    description: str
    tone: str | None
    mood: str | None
    image_prompt: str | None
    image_path: str | None
    image_status: str
    video_prompt: str | None
    video_path: str | None
    video_status: str
    video_duration: float
    video_provider: str | None
    video_model: str | None

    model_config = {"from_attributes": True}


class StoryboardResponse(BaseModel):
    id: int
    script_id: int
    total_shots: int
    total_duration: int | None
    tone_mapping: dict | None
    shots: list[ShotResponse] = []
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
