import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publish import SocialAccount, PublishRecord
from app.models.project import WorkflowStep
from app.schemas.publish import AddSocialAccountRequest, PublishRequest
from app.utils.logger import logger


class PublishService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_social_accounts(self, user_id: int) -> list[SocialAccount]:
        result = await self.db.execute(
            select(SocialAccount).where(SocialAccount.user_id == user_id)
        )
        return result.scalars().all()

    async def add_social_account(self, user_id: int, data: AddSocialAccountRequest) -> SocialAccount:
        # Validate cookies before creating the account
        if data.auth_data:
            valid = await self._validate_cookies(data.platform, data.auth_data)
            if not valid:
                raise ValueError("Cookie validation failed — cookies are invalid or expired")

        account = SocialAccount(
            user_id=user_id,
            platform=data.platform,
            account_name=data.account_name,
            account_id=data.account_id,
            auth_data=json.dumps(data.auth_data) if data.auth_data else None,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        logger.info(f"Social account added: {account.id} - {data.platform}/{data.account_name}")
        return account

    async def delete_social_account(self, account_id: int) -> bool:
        result = await self.db.execute(
            select(SocialAccount).where(SocialAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return False
        await self.db.delete(account)
        await self.db.commit()
        return True

    async def publish(self, project_id: int, user_id: int, data: PublishRequest) -> dict:
        """Create a PublishRecord and dispatch Celery publish task."""
        # Verify the social account belongs to the current user and is active
        account = await self.db.get(SocialAccount, data.account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Social account not found or does not belong to user")
        if not account.is_active:
            raise ValueError("Social account is not active")

        # Create publish record
        record = PublishRecord(
            project_id=project_id,
            account_id=data.account_id,
            asset_id=data.asset_id,
            title=data.title,
            description=data.description,
            tags=json.dumps(data.tags) if data.tags else None,
            status="pending",
        )
        self.db.add(record)

        # Create workflow step for progress tracking
        step = WorkflowStep(
            project_id=project_id,
            step_name=f"publish_{account.platform}",
            step_order=0,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.db.add(step)

        await self.db.commit()
        await self.db.refresh(record)
        await self.db.refresh(step)

        # Dispatch Celery task
        from app.worker.tasks.publish import publish_video_task

        task = publish_video_task.delay(record.id, step.id)

        # Store celery task id on the workflow step
        step.celery_task_id = task.id
        await self.db.commit()

        logger.info(f"Publish task dispatched: record={record.id}, task={task.id}, platform={account.platform}")
        return {
            "record_id": record.id,
            "task_id": task.id,
            "status": "pending",
            "platform": account.platform,
        }

    async def validate_account_cookies(self, account_id: int, user_id: int) -> bool:
        """Validate cookies for a social account."""
        account = await self.db.get(SocialAccount, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Social account not found")
        cookies = json.loads(account.auth_data) if account.auth_data else {}
        return await self._validate_cookies(account.platform, cookies)

    async def get_publish_status(self, record_id: int) -> dict | None:
        """Get publish record status including workflow step progress."""
        record = await self.get_publish_record(record_id)
        if not record:
            return None

        result = {
            "record_id": record.id,
            "status": record.status,
            "platform_post_id": record.platform_post_id,
            "platform_url": record.platform_url,
            "error_message": record.error_message,
            "published_at": record.published_at.isoformat() if record.published_at else None,
        }

        # Find associated workflow step
        stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.project_id == record.project_id)
            .where(WorkflowStep.step_name == f"publish_%")
            .order_by(WorkflowStep.id.desc())
            .limit(1)
        )
        step_result = await self.db.execute(stmt)
        step = step_result.scalar_one_or_none()
        if step:
            result["progress"] = step.progress
            result["step_status"] = step.status
            result["step_error"] = step.error_message

        return result

    async def list_publish_records(self, project_id: int) -> list[PublishRecord]:
        result = await self.db.execute(
            select(PublishRecord).where(PublishRecord.project_id == project_id)
        )
        return result.scalars().all()

    async def get_publish_record(self, record_id: int) -> PublishRecord | None:
        result = await self.db.execute(
            select(PublishRecord).where(PublishRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def sync_analytics(self, record_id: int) -> dict:
        """Sync analytics from platform. Returns sync result."""
        record = await self.get_publish_record(record_id)
        if not record:
            raise ValueError("Publish record not found")
        # TODO: Implement platform-specific analytics sync
        return {"record_id": record_id, "status": "pending_implementation"}

    # ── internal helpers ─────────────────────────────────────────────────────

    async def _validate_cookies(self, platform: str, cookies: dict) -> bool:
        from app.services.publishers.registry import publisher_registry

        publisher = publisher_registry.get_publisher(platform)
        if not publisher:
            return False
        return await publisher.validate_cookies(cookies)
