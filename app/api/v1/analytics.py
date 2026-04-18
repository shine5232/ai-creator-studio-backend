from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    AIUsageResponse, ContentPerformanceResponse,
    CostSummaryResponse, GenerationCostResponse, OverviewResponse, QuotaResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.get_overview(current_user.id)


@router.get("/generation-costs")
async def get_generation_costs(
    provider: str | None = None,
    since: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    records, summaries = await service.get_generation_costs(current_user.id, provider, since)
    return {
        "records": [GenerationCostResponse.model_validate(r).model_dump() for r in records],
        "summary": summaries,
    }


@router.get("/content-performance")
async def get_content_performance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_content_performance(current_user.id)
    return [ContentPerformanceResponse.model_validate(d).model_dump() for d in data]


@router.get("/ai-usage")
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.get_ai_usage(current_user.id)


@router.get("/quotas")
async def get_quotas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    quotas = await service.get_quotas(current_user.id)
    result = []
    for q in quotas:
        result.append({
            "quota_type": q.quota_type,
            "used_count": q.used_count,
            "limit_count": q.limit_count,
            "period": q.period,
            "remaining": q.limit_count - q.used_count,
        })
    return result
