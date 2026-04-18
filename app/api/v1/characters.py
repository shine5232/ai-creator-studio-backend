from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.character import (
    CharacterResponse, CreateCharacterRequest,
    GenerateReferenceRequest, UpdateCharacterRequest,
)
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Characters"])


@router.get("/projects/{project_id}/characters")
async def list_characters(
    project_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = CharacterService(db)
    chars = await service.list_characters(project_id)
    start = (page - 1) * page_size
    page_items = chars[start:start + page_size]
    return {
        "items": [CharacterResponse.model_validate(c).model_dump() for c in page_items],
        "total": len(chars),
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (len(chars) + page_size - 1) // page_size),
    }


@router.post("/projects/{project_id}/characters", response_model=CharacterResponse, status_code=201)
async def create_character(
    project_id: int,
    data: CreateCharacterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = CharacterService(db)
    return await service.create_character(project_id, data)


@router.get("/characters/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CharacterService(db)
    char = await service.get_character(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@router.put("/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    data: UpdateCharacterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CharacterService(db)
    try:
        return await service.update_character(character_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CharacterService(db)
    if not await service.delete_character(character_id):
        raise HTTPException(status_code=404, detail="Character not found")
    return {"message": "Character deleted"}


@router.post("/characters/{character_id}/generate-reference")
async def generate_reference(
    character_id: int,
    data: GenerateReferenceRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CharacterService(db)
    try:
        provider = data.provider if data else None
        return await service.generate_reference_image(character_id, provider)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
