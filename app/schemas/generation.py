from pydantic import BaseModel, Field


# --- Requests ---

class BatchGenerateImagesRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    shot_ids: list[int] | None = None  # None = all pending shots


class BatchGenerateVideosRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    shot_ids: list[int] | None = None


class MergeVideosRequest(BaseModel):
    shot_ids: list[int] = []
    add_background_music: bool = False
    music_path: str | None = None


class RetryTaskRequest(BaseModel):
    params: dict = Field(default_factory=dict)


class AddMusicRequest(BaseModel):
    music_path: str | None = None


# --- Responses ---

class GenerationTaskResponse(BaseModel):
    task_id: str
    task_type: str
    project_id: int
    status: str
    progress: int
    current: int | None = None
    total: int | None = None
    message: str | None = None
