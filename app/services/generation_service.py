from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.script import Script, Shot, Storyboard
from app.models.project import Project, WorkflowStep
from app.models.character import Character
from app.utils.logger import logger


class GenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_images_batch(
        self, project_id: int, provider: str | None = None, model: str | None = None,
        shot_ids: list[int] | None = None, user_id: int | None = None,
    ) -> dict:
        """Batch generate images for shots. Returns task info."""
        shots = await self._get_pending_shots(project_id, "image", shot_ids)
        if not shots:
            return {"task_id": None, "message": "No pending shots for image generation"}

        # Create WorkflowStep record
        step = WorkflowStep(
            project_id=project_id,
            step_name="generate_images",
            step_order=0,
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        # Dispatch Celery task
        from app.worker.tasks.generation import generate_images_for_shots

        result = generate_images_for_shots.delay(
            shot_ids=[s.id for s in shots],
            project_id=project_id,
            provider=provider,
            model=model,
            workflow_step_id=step.id,
            user_id=user_id,
        )

        # Store real Celery task ID
        step.celery_task_id = result.id
        await self.db.commit()

        logger.info(f"Dispatched image generation task {result.id}: {len(shots)} shots for project {project_id}")
        return {
            "task_id": result.id,
            "task_type": "generate_images",
            "project_id": project_id,
            "status": "pending",
            "total": len(shots),
            "shot_ids": [s.id for s in shots],
        }

    async def generate_videos_batch(
        self, project_id: int, provider: str | None = None, model: str | None = None,
        shot_ids: list[int] | None = None, user_id: int | None = None,
    ) -> dict:
        """Batch generate videos for shots. Returns task info."""
        shots = await self._get_pending_shots(project_id, "video", shot_ids)
        if not shots:
            return {"task_id": None, "message": "No pending shots for video generation"}

        # Create WorkflowStep record
        step = WorkflowStep(
            project_id=project_id,
            step_name="generate_videos",
            step_order=0,
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        # Dispatch Celery task
        from app.worker.tasks.generation import generate_videos_for_shots

        result = generate_videos_for_shots.delay(
            shot_ids=[s.id for s in shots],
            project_id=project_id,
            provider=provider,
            model=model,
            workflow_step_id=step.id,
            user_id=user_id,
        )

        step.celery_task_id = result.id
        await self.db.commit()

        logger.info(f"Dispatched video generation task {result.id}: {len(shots)} shots for project {project_id}")
        return {
            "task_id": result.id,
            "task_type": "generate_videos",
            "project_id": project_id,
            "status": "pending",
            "total": len(shots),
            "shot_ids": [s.id for s in shots],
        }

    async def merge_videos(self, project_id: int, add_music: bool = False, music_path: str | None = None, shot_ids: list[int] | None = None) -> dict:
        """Merge shot videos into final output. Returns task info."""
        project = await self.db.execute(select(Project).where(Project.id == project_id))
        if not project.scalar_one_or_none():
            raise ValueError("Project not found")

        # Create WorkflowStep record
        step = WorkflowStep(
            project_id=project_id,
            step_name="merge_videos",
            step_order=0,
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        # Dispatch Celery task
        from app.worker.tasks.generation import merge_project_videos

        result = merge_project_videos.delay(
            project_id=project_id,
            add_music=add_music,
            music_path=music_path,
            shot_ids=shot_ids,
            workflow_step_id=step.id,
        )

        step.celery_task_id = result.id
        await self.db.commit()

        logger.info(f"Dispatched merge task {result.id} for project {project_id}")
        return {
            "task_id": result.id,
            "task_type": "merge_videos",
            "project_id": project_id,
            "status": "pending",
        }

    async def _get_pending_shots(
        self, project_id: int, gen_type: str, shot_ids: list[int] | None = None,
    ) -> list[Shot]:
        status_field = Shot.image_status if gen_type == "image" else Shot.video_status

        query = (
            select(Shot)
            .join(Storyboard, Shot.storyboard_id == Storyboard.id)
            .join(Script, Storyboard.script_id == Script.id)
            .where(Script.project_id == project_id)
            .where(status_field == "pending")
            .order_by(Shot.shot_number)
        )

        if shot_ids:
            query = query.where(Shot.id.in_(shot_ids))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_image_prompts(
        self, shot_ids: list[int], project_id: int,
    ) -> dict:
        """派发 Celery 任务为指定分镜生成 Seedream 文生图提示词。"""
        if not shot_ids:
            return {"task_id": None, "message": "没有需要生成提示词的分镜"}

        step = WorkflowStep(
            project_id=project_id,
            step_name="generate_image_prompts",
            step_order=0,
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        from app.worker.tasks.generation import generate_image_prompts_for_shots

        result = generate_image_prompts_for_shots.delay(
            shot_ids=shot_ids,
            workflow_step_id=step.id,
        )

        step.celery_task_id = result.id
        await self.db.commit()

        logger.info(f"Dispatched prompt generation task {result.id}: {len(shot_ids)} shots for project {project_id}")
        return {
            "task_id": result.id,
            "task_type": "generate_image_prompts",
            "project_id": project_id,
            "status": "pending",
            "total": len(shot_ids),
            "shot_ids": shot_ids,
        }

    async def batch_generate_character_images(
        self, project_id: int, aspect_ratio: str = "9:16",
        user_id: int | None = None,
    ) -> dict:
        """批量生成该项目所有人物的多角度参考图。"""
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = list(result.scalars().all())

        if not characters:
            return {"task_id": None, "message": "没有需要生成图片的人物"}

        step = WorkflowStep(
            project_id=project_id,
            step_name="generate_character_images",
            step_order=0,
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        from app.worker.tasks.generation import generate_character_multi_angle_images

        celery_result = generate_character_multi_angle_images.delay(
            character_ids=[c.id for c in characters],
            project_id=project_id,
            aspect_ratio=aspect_ratio,
            workflow_step_id=step.id,
            user_id=user_id,
        )

        step.celery_task_id = celery_result.id
        await self.db.commit()

        logger.info(f"Dispatched multi-angle character image task {celery_result.id}: {len(characters)} characters for project {project_id}")
        return {
            "task_id": celery_result.id,
            "task_type": "generate_character_images",
            "project_id": project_id,
            "status": "pending",
            "total": len(characters),
        }
