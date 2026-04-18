from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.publish import (
    AddSocialAccountRequest, PublishRecordResponse,
    PublishRequest, PublishStatusResponse, SocialAccountResponse,
)
from app.services.publish_service import PublishService

router = APIRouter(tags=["Publishing"])


@router.get("/social-accounts")
async def list_social_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    accounts = await service.list_social_accounts(current_user.id)
    return [SocialAccountResponse.model_validate(a).model_dump() for a in accounts]


@router.post("/social-accounts", response_model=SocialAccountResponse, status_code=201)
async def add_social_account(
    data: AddSocialAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    try:
        return await service.add_social_account(current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/social-accounts/{account_id}")
async def delete_social_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    if not await service.delete_social_account(account_id):
        raise HTTPException(status_code=404, detail="Social account not found")
    return {"message": "Social account deleted"}


@router.post("/social-accounts/{account_id}/validate-cookies")
async def validate_cookies(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    try:
        valid = await service.validate_account_cookies(account_id, current_user.id)
        return {"account_id": account_id, "valid": valid}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/publish", status_code=201)
async def publish(
    project_id: int,
    data: PublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.project_service import ProjectService
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = PublishService(db)
    try:
        return await service.publish(project_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/publish-records")
async def list_publish_records(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.project_service import ProjectService
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = PublishService(db)
    records = await service.list_publish_records(project_id)
    return [PublishRecordResponse.model_validate(r).model_dump() for r in records]


@router.get("/publish-records/{record_id}", response_model=PublishRecordResponse)
async def get_publish_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    record = await service.get_publish_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publish record not found")
    return record


@router.get("/publish-records/{record_id}/status", response_model=PublishStatusResponse)
async def get_publish_status(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    result = await service.get_publish_status(record_id)
    if not result:
        raise HTTPException(status_code=404, detail="Publish record not found")
    return result


@router.post("/publish-records/{record_id}/sync-analytics")
async def sync_analytics(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PublishService(db)
    try:
        return await service.sync_analytics(record_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
