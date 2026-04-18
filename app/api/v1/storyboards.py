from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.script import Shot, Storyboard, Script
from app.models.user import User
from app.schemas.storyboard import (
    CreateStoryboardRequest, ShotResponse, StoryboardResponse,
    UpdateShotRequest, RegenerateImageRequest, RegenerateVideoRequest,
)
from app.services.generation_service import GenerationService
from app.services.storyboard_service import StoryboardService

router = APIRouter(tags=["Storyboards"])


@router.get("/scripts/{script_id}/storyboard", response_model=StoryboardResponse)
async def get_storyboard(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    storyboard = await service.get_storyboard(script_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return storyboard


@router.post("/scripts/{script_id}/storyboard", response_model=StoryboardResponse, status_code=201)
async def create_storyboard(
    script_id: int,
    data: CreateStoryboardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    try:
        return await service.create_storyboard(script_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/storyboards/{storyboard_id}", response_model=StoryboardResponse)
async def get_storyboard_detail(
    storyboard_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    storyboard = await service.get_storyboard_detail(storyboard_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return storyboard


@router.put("/shots/{shot_id}", response_model=ShotResponse)
async def update_shot(
    shot_id: int,
    data: UpdateShotRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    try:
        return await service.update_shot(shot_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/shots/{shot_id}/regenerate-image")
async def regenerate_image(
    shot_id: int,
    data: RegenerateImageRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    # Resolve project_id and verify ownership
    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    # Update prompt if provided, then reset status
    if data and data.image_prompt:
        shot.image_prompt = data.image_prompt
    shot.image_status = "pending"
    await db.commit()

    service = GenerationService(db)
    return await service.generate_images_batch(
        project_id,
        provider=data.provider if data else None,
        model=data.model if data else None,
        shot_ids=[shot_id],
    )


@router.post("/shots/{shot_id}/regenerate-video")
async def regenerate_video(
    shot_id: int,
    data: RegenerateVideoRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    if data and data.video_prompt:
        shot.video_prompt = data.video_prompt
    if data and data.duration:
        shot.video_duration = data.duration
    shot.video_status = "pending"
    await db.commit()

    service = GenerationService(db)
    return await service.generate_videos_batch(
        project_id,
        provider=data.provider if data else None,
        model=data.model if data else None,
        shot_ids=[shot_id],
    )


async def _get_shot_project_id(db: AsyncSession, shot: Shot) -> int:
    """Resolve project_id from a Shot via Storyboard→Script chain."""
    result = await db.execute(
        select(Script.project_id)
        .join(Storyboard, Storyboard.script_id == Script.id)
        .where(Storyboard.id == shot.storyboard_id)
    )
    return result.scalar_one()


async def _verify_project_owner(db: AsyncSession, project_id: int, user_id: int) -> bool:
    from app.models.project import Project
    result = await db.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None
