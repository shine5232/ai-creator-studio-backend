from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user_ai_config import (
    UserAIConfigCreate,
    UserAIConfigUpdate,
    UserAIConfigResponse,
    UserAIConfigListResponse,
)
from app.services.user_ai_config_service import UserAIConfigService
from app.ai_gateway.registry import registry

router = APIRouter(prefix="/user-ai-configs", tags=["User AI Configs"])


@router.get("", response_model=UserAIConfigListResponse)
async def list_configs(
    service_type: str | None = Query(None, description="Filter by service type"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserAIConfigService(db)
    configs = await service.list_configs(user.id, service_type)
    return UserAIConfigListResponse(
        items=[UserAIConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
    )


@router.get("/system-defaults")
async def get_system_defaults(
    user: User = Depends(get_current_user),
):
    """Return system default providers/models for reference."""
    providers = registry.list_providers()
    return [
        {
            "name": p.provider_name,
            "services": [s.value for s in p.supported_services],
            "models": p.get_models(),
        }
        for p in providers
    ]


@router.get("/{config_id}", response_model=UserAIConfigResponse)
async def get_config(
    config_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserAIConfigService(db)
    config = await service.get_config(config_id, user.id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return UserAIConfigResponse.model_validate(config)


@router.post("", response_model=UserAIConfigResponse, status_code=201)
async def create_config(
    data: UserAIConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate service_type
    valid_types = {"text_generation", "text_to_image", "image_to_image", "image_to_video"}
    if data.service_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service_type. Valid: {sorted(valid_types)}",
        )

    # Validate extra_config is valid JSON if provided
    if data.extra_config:
        try:
            import json
            json.loads(data.extra_config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="extra_config must be valid JSON")

    service = UserAIConfigService(db)
    config = await service.create_config(user.id, data)
    return UserAIConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=UserAIConfigResponse)
async def update_config(
    config_id: int,
    data: UserAIConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate service_type if provided
    if data.service_type:
        valid_types = {"text_generation", "text_to_image", "image_to_image", "image_to_video"}
        if data.service_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid service_type. Valid: {sorted(valid_types)}",
            )

    # Validate extra_config is valid JSON if provided
    if data.extra_config:
        try:
            import json
            json.loads(data.extra_config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="extra_config must be valid JSON")

    service = UserAIConfigService(db)
    config = await service.update_config(config_id, user.id, data)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return UserAIConfigResponse.model_validate(config)


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserAIConfigService(db)
    deleted = await service.delete_config(config_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"success": True, "message": "Config deleted"}
