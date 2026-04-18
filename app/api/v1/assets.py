from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.asset import AssetResponse
from app.services.asset_service import AssetService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Assets"])


@router.get("/projects/{project_id}/assets")
async def list_assets(
    project_id: int,
    asset_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = AssetService(db)
    assets = await service.list_assets(project_id, asset_type)
    start = (page - 1) * page_size
    page_items = assets[start:start + page_size]
    return {
        "items": [AssetResponse.model_validate(a).model_dump() for a in page_items],
        "total": len(assets),
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (len(assets) + page_size - 1) // page_size),
    }


@router.post("/projects/{project_id}/assets/upload", response_model=AssetResponse, status_code=201)
async def upload_asset(
    project_id: int,
    file: UploadFile = File(...),
    asset_type: str = "image",
    category: str | None = None,
    shot_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save file
    import os
    upload_dir = f"data/uploads/{project_id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename or "upload")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    service = AssetService(db)
    asset = await service.create_asset(
        project_id=project_id,
        file_path=file_path,
        file_name=file.filename or "upload",
        asset_type=asset_type,
        category=category,
        shot_id=shot_id,
        mime_type=file.content_type,
        file_size=len(content),
    )
    return asset


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssetService(db)
    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import FileResponse as FR

    service = AssetService(db)
    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    import os
    if not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FR(asset.file_path, filename=asset.file_name)


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AssetService(db)
    if not await service.delete_asset(asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted"}
