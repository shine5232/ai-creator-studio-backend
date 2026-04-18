from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project, WorkflowStep
from app.schemas.generation import (
    AddMusicRequest, BatchGenerateImagesRequest, BatchGenerateVideosRequest,
    MergeVideosRequest, RetryTaskRequest,
)
from app.services.generation_service import GenerationService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Generation"])


@router.post("/projects/{project_id}/generate/images")
async def batch_generate_images(
    project_id: int,
    data: BatchGenerateImagesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = GenerationService(db)
    return await service.generate_images_batch(
        project_id, data.provider, data.model, data.shot_ids,
    )


@router.post("/projects/{project_id}/generate/videos")
async def batch_generate_videos(
    project_id: int,
    data: BatchGenerateVideosRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = GenerationService(db)
    return await service.generate_videos_batch(
        project_id, data.provider, data.model, data.shot_ids,
    )


@router.post("/projects/{project_id}/generate/merge")
async def merge_videos(
    project_id: int,
    data: MergeVideosRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = GenerationService(db)
    return await service.merge_videos(project_id, data.add_background_music, data.music_path)


@router.post("/projects/{project_id}/generate/music")
async def add_music(
    project_id: int,
    data: AddMusicRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_project(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    service = GenerationService(db)
    return await service.merge_videos(
        project_id, add_music=True, music_path=data.music_path if data else None,
    )


@router.get("/generation/tasks")
async def list_generation_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all WorkflowStep tasks for the current user's projects."""
    result = await db.execute(
        select(WorkflowStep)
        .join(Project)
        .where(Project.user_id == current_user.id)
        .order_by(WorkflowStep.created_at.desc())
    )
    steps = result.scalars().all()

    tasks = []
    for step in steps:
        tasks.append({
            "task_id": step.celery_task_id,
            "workflow_step_id": step.id,
            "task_type": step.step_name,
            "project_id": step.project_id,
            "status": step.status,
            "progress": step.progress,
            "error_message": step.error_message,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        })
    return {"tasks": tasks}


@router.get("/generation/tasks/{task_id}")
async def get_generation_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a generation task by combining Celery + DB data."""
    # Look up the WorkflowStep by celery_task_id
    result = await db.execute(
        select(WorkflowStep)
        .join(Project)
        .where(WorkflowStep.celery_task_id == task_id, Project.user_id == current_user.id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Task not found")

    response = {
        "task_id": task_id,
        "task_type": step.step_name,
        "project_id": step.project_id,
        "status": step.status,
        "progress": step.progress,
        "error_message": step.error_message,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
    }

    # Try to get live Celery state
    try:
        from celery.result import AsyncResult
        from app.worker.celery_app import celery_app

        async_result = AsyncResult(task_id, app=celery_app)
        if async_result.state == "PROGRESS" and async_result.info:
            response["progress"] = async_result.info.get("progress", step.progress)
            response["message"] = async_result.info.get("message", "")
            response["status"] = "running"
        elif async_result.state == "FAILURE":
            response["status"] = "failed"
            response["error_message"] = str(async_result.result)[:2000]
        elif async_result.state == "SUCCESS":
            response["status"] = "completed"
            response["progress"] = 100
    except Exception:
        pass  # Celery may not be available in eager mode or if broker is down

    return response


@router.post("/generation/tasks/{task_id}/retry")
async def retry_generation_task(
    task_id: str,
    data: RetryTaskRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed generation task by re-dispatching with original parameters."""
    result = await db.execute(
        select(WorkflowStep)
        .join(Project)
        .where(WorkflowStep.celery_task_id == task_id, Project.user_id == current_user.id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Task not found")

    if step.status not in ("failed",):
        raise HTTPException(status_code=400, detail=f"Cannot retry task with status '{step.status}'")

    # Create a new WorkflowStep for the retry
    new_step = WorkflowStep(
        project_id=step.project_id,
        step_name=step.step_name,
        step_order=step.step_order,
        status="running",
        progress=0,
        started_at=__import__("datetime").datetime.utcnow(),
    )
    db.add(new_step)
    await db.flush()

    # Re-dispatch based on task type
    from app.worker.tasks.generation import (
        generate_images_for_shots,
        generate_videos_for_shots,
        merge_project_videos,
    )

    params = data.params if data else {}

    if step.step_name == "generate_images":
        shot_ids = params.get("shot_ids", [])
        new_result = generate_images_for_shots.delay(
            shot_ids=shot_ids,
            project_id=step.project_id,
            provider=params.get("provider"),
            model=params.get("model"),
            workflow_step_id=new_step.id,
        )
    elif step.step_name == "generate_videos":
        shot_ids = params.get("shot_ids", [])
        new_result = generate_videos_for_shots.delay(
            shot_ids=shot_ids,
            project_id=step.project_id,
            provider=params.get("provider"),
            model=params.get("model"),
            workflow_step_id=new_step.id,
        )
    elif step.step_name == "merge_videos":
        new_result = merge_project_videos.delay(
            project_id=step.project_id,
            add_music=params.get("add_music", False),
            music_path=params.get("music_path"),
            workflow_step_id=new_step.id,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown task type: {step.step_name}")

    new_step.celery_task_id = new_result.id
    await db.flush()

    return {
        "task_id": new_result.id,
        "task_type": step.step_name,
        "project_id": step.project_id,
        "status": "pending",
        "original_task_id": task_id,
    }
