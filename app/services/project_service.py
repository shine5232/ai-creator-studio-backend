import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, WorkflowStep
from app.schemas.project import CreateProjectRequest, UpdateProjectRequest, StartWorkflowRequest
from app.utils.logger import logger


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, user_id: int, page: int = 1, page_size: int = 20) -> tuple[list[Project], int]:
        query = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        total_result = await self.db.execute(
            select(Project).where(Project.user_id == user_id)
        )
        all_rows = total_result.scalars().all()
        total = len(all_rows)

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def create_project(self, user_id: int, data: CreateProjectRequest) -> Project:
        project = Project(
            user_id=user_id,
            name=data.name,
            description=data.description,
            source_url=data.source_url,
            source_platform=data.source_platform,
            reference_case_id=data.reference_case_id,
            output_duration=data.output_duration,
            settings=json.dumps(data.settings) if data.settings else None,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        logger.info(f"Project created: {project.id} - {project.name}")
        return project

    async def get_project(self, project_id: int) -> Project | None:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def update_project(self, project_id: int, data: UpdateProjectRequest) -> Project:
        project = await self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "settings" and value is not None:
                value = json.dumps(value)
            setattr(project, field, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int) -> bool:
        project = await self.get_project(project_id)
        if not project:
            return False
        await self.db.delete(project)
        await self.db.commit()
        return True

    async def get_workflow(self, project_id: int) -> list[WorkflowStep]:
        result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.project_id == project_id)
            .order_by(WorkflowStep.step_order)
        )
        return result.scalars().all()

    async def start_workflow(self, project_id: int, data: StartWorkflowRequest) -> list[WorkflowStep]:
        project = await self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        if project.status not in ("draft", "failed"):
            raise ValueError(f"Cannot start workflow in status: {project.status}")

        # Create workflow steps
        steps = []
        for i, step_name in enumerate(data.steps):
            step = WorkflowStep(
                project_id=project_id,
                step_name=step_name,
                step_order=i,
                status="pending",
            )
            self.db.add(step)
            steps.append(step)

        project.status = "analyzing"
        await self.db.commit()
        logger.info(f"Workflow started for project {project_id} with {len(steps)} steps")
        return steps
