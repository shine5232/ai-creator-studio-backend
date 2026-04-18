from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.asset import Asset
from app.models.publish import PublishRecord
from app.models.analytics import ContentAnalytics, GenerationCost
from app.models.user import User, UserQuota
from app.utils.logger import logger


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self, user_id: int) -> dict:
        project_count = await self.db.scalar(
            select(func.count(Project.id)).where(Project.user_id == user_id)
        ) or 0
        asset_count = await self.db.scalar(
            select(func.count(Asset.id)).where(Asset.project_id.in_(
                select(Project.id).where(Project.user_id == user_id)
            ))
        ) or 0
        published_count = await self.db.scalar(
            select(func.count(PublishRecord.id)).where(PublishRecord.project_id.in_(
                select(Project.id).where(Project.user_id == user_id)
            ))
        ) or 0
        total_cost = await self.db.scalar(
            select(func.sum(GenerationCost.cost_amount)).where(GenerationCost.user_id == user_id)
        ) or 0.0

        return {
            "total_projects": project_count,
            "total_assets": asset_count,
            "total_published": published_count,
            "total_cost": float(total_cost),
        }

    async def get_generation_costs(
        self, user_id: int, provider: str | None = None,
        since: str | None = None,
    ) -> tuple[list[GenerationCost], list[dict]]:
        query = select(GenerationCost).where(GenerationCost.user_id == user_id)
        if provider:
            query = query.where(GenerationCost.provider == provider)

        result = await self.db.execute(query.order_by(GenerationCost.created_at.desc()).limit(100))
        records = result.scalars().all()

        # Summary
        summary_query = (
            select(
                GenerationCost.provider,
                GenerationCost.model,
                func.count(GenerationCost.id).label("total_calls"),
                func.sum(GenerationCost.cost_amount).label("total_cost"),
            )
            .where(GenerationCost.user_id == user_id)
            .group_by(GenerationCost.provider, GenerationCost.model)
        )
        if provider:
            summary_query = summary_query.where(GenerationCost.provider == provider)

        summary_result = await self.db.execute(summary_query)
        summaries = [
            {
                "provider": row.provider,
                "model": row.model,
                "total_calls": row.total_calls,
                "total_cost": float(row.total_cost or 0),
            }
            for row in summary_result.all()
        ]

        return records, summaries

    async def get_content_performance(self, user_id: int) -> list[ContentAnalytics]:
        result = await self.db.execute(
            select(ContentAnalytics)
            .where(ContentAnalytics.project_id.in_(
                select(Project.id).where(Project.user_id == user_id)
            ))
            .order_by(ContentAnalytics.recorded_at.desc())
        )
        return result.scalars().all()

    async def get_ai_usage(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(
                GenerationCost.provider,
                GenerationCost.service_type,
                func.count(GenerationCost.id).label("total_calls"),
                func.sum(GenerationCost.input_tokens + GenerationCost.output_tokens).label("total_tokens"),
                func.sum(GenerationCost.cost_amount).label("total_cost"),
            )
            .where(GenerationCost.user_id == user_id)
            .group_by(GenerationCost.provider, GenerationCost.service_type)
        )
        return [
            {
                "provider": row.provider,
                "service_type": row.service_type,
                "total_calls": row.total_calls,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0),
            }
            for row in result.all()
        ]

    async def get_quotas(self, user_id: int) -> list[UserQuota]:
        result = await self.db.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        return result.scalars().all()
