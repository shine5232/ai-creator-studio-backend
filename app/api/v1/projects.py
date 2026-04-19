from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project, WorkflowStep
from app.models.script import Script, Storyboard, Shot
from app.schemas.project import (
    CreateProjectRequest, ProjectDetailResponse, ProjectResponse,
    StartWorkflowRequest, UpdateProjectRequest, WorkflowStepResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("")
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    projects, total = await service.list_projects(current_user.id, page, page_size)

    # 批量查询每个项目的第一个分镜图片作为封面
    project_ids = [p.id for p in projects]
    cover_map: dict[int, str | None] = {}
    if project_ids:
        cover_result = await db.execute(
            select(Script.project_id, Shot.image_path)
            .join(Storyboard, Storyboard.script_id == Script.id)
            .join(Shot, Shot.storyboard_id == Storyboard.id)
            .where(Script.project_id.in_(project_ids))
            .where(Shot.image_path != None)  # noqa: E711
            .where(Shot.image_path != "")
            .order_by(Script.project_id, Shot.shot_number)
        )
        for pid, img_path in cover_result.all():
            if pid not in cover_map:
                cover_map[pid] = img_path

    items = []
    for p in projects:
        d = ProjectResponse.model_validate(p).model_dump()
        d["cover_image_path"] = cover_map.get(p.id)
        items.append(d)

    # 统计数据
    video_count_result = await db.execute(
        select(func.count(Shot.id))
        .join(Storyboard, Shot.storyboard_id == Storyboard.id)
        .join(Script, Storyboard.script_id == Script.id)
        .join(Project, Project.id == Script.project_id)
        .where(Project.user_id == current_user.id)
        .where(Shot.video_status == "completed")
    )
    video_count = video_count_result.scalar() or 0

    workflow_count_result = await db.execute(
        select(func.count(WorkflowStep.id))
        .join(Project, Project.id == WorkflowStep.project_id)
        .where(Project.user_id == current_user.id)
        .where(WorkflowStep.status == "completed")
    )
    workflow_count = workflow_count_result.scalar() or 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": {
            "projects": total,
            "videos": video_count,
            "aiCalls": workflow_count,
            "cost": "0.00",
        },
    }


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.create_project(current_user.id, data)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return await service.update_project(project_id, data)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    await service.delete_project(project_id)
    return {"message": "Project deleted"}


@router.get("/{project_id}/workflow")
async def get_workflow(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    steps = await service.get_workflow(project_id)
    return [WorkflowStepResponse.model_validate(s).model_dump() for s in steps]


@router.post("/{project_id}/start")
async def start_workflow(
    project_id: int,
    data: StartWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        steps = await service.start_workflow(project_id, data)
        return {
            "project_id": project_id,
            "status": "started",
            "workflow_steps": [
                {"step_name": s.step_name, "status": s.status, "step_order": s.step_order}
                for s in steps
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
