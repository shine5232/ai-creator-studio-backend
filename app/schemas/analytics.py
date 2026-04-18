from datetime import datetime

from pydantic import BaseModel


# --- Responses ---

class OverviewResponse(BaseModel):
    total_projects: int = 0
    total_assets: int = 0
    total_published: int = 0
    total_cost: float = 0.0


class GenerationCostResponse(BaseModel):
    id: int
    project_id: int | None
    provider: str
    model: str
    service_type: str
    shot_id: int | None
    input_tokens: int | None
    output_tokens: int | None
    api_calls: int
    cost_amount: float
    currency: str
    duration_ms: int | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class CostSummaryResponse(BaseModel):
    provider: str
    model: str
    total_calls: int
    total_cost: float


class ContentPerformanceResponse(BaseModel):
    project_id: int
    platform: str | None
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    engagement_rate: float | None
    recorded_at: datetime | None

    model_config = {"from_attributes": True}


class AIUsageResponse(BaseModel):
    provider: str
    service_type: str
    total_calls: int
    total_tokens: int
    total_cost: float


class QuotaResponse(BaseModel):
    quota_type: str
    used_count: int
    limit_count: int
    period: str
    remaining: int

    model_config = {"from_attributes": True}
