from datetime import datetime

from pydantic import BaseModel


# --- Responses ---

class AssetResponse(BaseModel):
    id: int
    project_id: int
    asset_type: str
    category: str | None
    file_name: str
    file_path: str
    file_size: int | None
    mime_type: str | None
    width: int | None
    height: int | None
    duration: float | None
    shot_id: int | None
    created_at: datetime | None

    model_config = {"from_attributes": True}
