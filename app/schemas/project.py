from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source_url: str | None = None
    source_platform: str | None = None
    reference_case_id: int | None = None
    output_duration: int | None = None
    settings: dict | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    output_duration: int | None = None
    settings: dict | None = None


class StartWorkflowRequest(BaseModel):
    steps: list[str] = Field(default_factory=lambda: [
        "download", "extract_frames", "analyze", "generate_script",
        "generate_storyboard", "generate_images", "generate_videos", "merge",
    ])


# --- Responses ---

class WorkflowStepResponse(BaseModel):
    id: int
    step_name: str
    step_order: int
    status: str
    progress: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    source_url: str | None
    source_platform: str | None
    reference_case_id: int | None
    output_duration: int | None
    settings: dict | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    workflow_steps: list[WorkflowStepResponse] = []
