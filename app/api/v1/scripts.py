from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.script import CreateScriptRequest, GenerateScriptRequest, ScriptResponse, UpdateScriptRequest
from app.services.script_service import ScriptService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Scripts"])


def _check_project(project_id: int, user: User, db):
    return ProjectService(db).get_project(project_id)


@router.get("/projects/{project_id}/scripts")
async def list_scripts(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _check_project(project_id, current_user, db)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = ScriptService(db)
    scripts = await service.list_scripts(project_id)
    return [ScriptResponse.model_validate(s).model_dump() for s in scripts]


@router.post("/projects/{project_id}/scripts/generate", response_model=ScriptResponse, status_code=201)
async def generate_script(
    project_id: int,
    data: GenerateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _check_project(project_id, current_user, db)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = ScriptService(db)
    try:
        return await service.generate_script(project_id, data)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/scripts", response_model=ScriptResponse, status_code=201)
async def create_script(
    project_id: int,
    data: CreateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _check_project(project_id, current_user, db)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = ScriptService(db)
    return await service.create_script(project_id, data)


@router.get("/scripts/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScriptService(db)
    script = await service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/scripts/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int,
    data: UpdateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScriptService(db)
    try:
        return await service.update_script(script_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/scripts/{script_id}")
async def delete_script(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScriptService(db)
    if not await service.delete_script(script_id):
        raise HTTPException(status_code=404, detail="Script not found")
    return {"message": "Script deleted"}


@router.post("/scripts/{script_id}/check-viral")
async def check_viral(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScriptService(db)
    try:
        return await service.check_viral(script_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scripts/{script_id}/markdown")
async def get_script_markdown(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取脚本的 Markdown 文件内容"""
    service = ScriptService(db)
    script = await service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if not script.script_path:
        raise HTTPException(status_code=404, detail="Script markdown file not found")

    file_path = Path(script.script_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Script markdown file not found on disk")

    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=file_path.name,
    )
