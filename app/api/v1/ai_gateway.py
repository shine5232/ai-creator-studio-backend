from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.key_manager import get_key_hint, store_key
from app.ai_gateway.registry import registry
from app.database import get_db
from app.models.analytics import GenerationCost
from app.utils.logger import logger

router = APIRouter()


# ─── Request / Response schemas ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    provider: str
    prompt: str
    service_type: str = "text_to_image"
    model: str | None = None
    image_url: str | None = None
    image_base64: str | None = None
    last_frame_url: str | None = None
    audio_url: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class AsyncGenerateRequest(GenerateRequest):
    """Same as GenerateRequest but for async providers."""
    pass


class StoreKeyRequest(BaseModel):
    provider: str
    api_key: str


class CostQueryParams(BaseModel):
    provider: str | None = None
    model: str | None = None
    service_type: str | None = None
    since: str | None = None  # ISO datetime


# ─── Provider endpoints ──────────────────────────────────────────────────────

@router.get("/providers")
async def list_providers():
    providers = registry.list_providers()
    return [
        {
            "name": p.provider_name,
            "services": [s.value for s in p.supported_services],
            "models": p.get_models(),
        }
        for p in providers
    ]


@router.get("/providers/{name}")
async def get_provider(name: str):
    provider = registry.get_provider(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    return {
        "name": provider.provider_name,
        "services": [s.value for s in provider.supported_services],
        "models": provider.get_models(),
    }


@router.get("/providers/{name}/models")
async def get_provider_models(name: str):
    provider = registry.get_provider(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    return provider.get_models()


# ─── Generation endpoints ────────────────────────────────────────────────────

@router.post("/generate")
async def generate(
    req: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = registry.get_provider(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    try:
        service_type = ServiceType(req.service_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service_type: {req.service_type}. "
                   f"Valid: {[s.value for s in ServiceType]}",
        )

    if not provider.supports(service_type):
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' does not support {req.service_type}",
        )

    ai_request = AIRequest(
        prompt=req.prompt,
        service_type=service_type,
        model=req.model,
        image_url=req.image_url,
        image_base64=req.image_base64,
        last_frame_url=req.last_frame_url,
        audio_url=req.audio_url,
        params=req.params,
    )

    response = await provider.generate(ai_request)

    # Record cost
    cost_record = GenerationCost(
        provider=req.provider,
        model=req.model or "default",
        service_type=req.service_type,
        cost_amount=response.cost,
    )
    db.add(cost_record)
    await db.commit()

    if not response.success:
        raise HTTPException(status_code=502, detail=response.error)

    return {
        "success": True,
        "data": response.data,
        "cost": response.cost,
    }


@router.post("/generate/async")
async def generate_async(
    req: AsyncGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = registry.get_provider(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    try:
        service_type = ServiceType(req.service_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid service_type: {req.service_type}")

    if not provider.supports(service_type):
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' does not support {req.service_type}",
        )

    ai_request = AIRequest(
        prompt=req.prompt,
        service_type=service_type,
        model=req.model,
        image_url=req.image_url,
        image_base64=req.image_base64,
        last_frame_url=req.last_frame_url,
        audio_url=req.audio_url,
        params=req.params,
    )

    response = await provider.generate(ai_request)

    # Record submission cost
    cost_record = GenerationCost(
        provider=req.provider,
        model=req.model or "default",
        service_type=req.service_type,
        cost_amount=response.cost,
    )
    db.add(cost_record)
    await db.commit()

    if not response.success:
        raise HTTPException(status_code=502, detail=response.error)

    return {
        "success": True,
        "task_id": response.task_id,
        "data": response.data,
    }


@router.get("/tasks/{task_id}")
async def check_task(
    task_id: str,
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    p = registry.get_provider(provider)
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    response = await p.check_task(task_id)

    # Update cost record if task completed (no-op: cost is recorded at submission)

    if not response.success:
        return {"success": False, "task_id": task_id, "error": response.error}

    return {
        "success": True,
        "task_id": task_id,
        "data": response.data,
    }


# ─── Key management ──────────────────────────────────────────────────────────

@router.post("/keys")
async def store_api_key(
    req: StoreKeyRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = registry.get_provider(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    try:
        await store_key(db, req.provider, req.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store key: {e}")
        raise HTTPException(status_code=500, detail="Failed to store API key. Check ENCRYPTION_KEY config.")

    return {"success": True, "message": f"API key stored for '{req.provider}'"}


@router.get("/keys/{provider}")
async def get_api_key_hint(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    p = registry.get_provider(provider)
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    hint = await get_key_hint(db, provider)
    if not hint:
        return {"provider": provider, "hint": None, "configured": False}
    return {"provider": provider, "hint": hint, "configured": True}


# ─── Cost tracking ───────────────────────────────────────────────────────────

@router.get("/costs")
async def get_costs(
    provider: str | None = None,
    model: str | None = None,
    service_type: str | None = None,
    since: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(GenerationCost)

    if provider:
        query = query.where(GenerationCost.provider == provider)
    if model:
        query = query.where(GenerationCost.model == model)
    if service_type:
        query = query.where(GenerationCost.service_type == service_type)
    if since:
        try:
            since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            query = query.where(GenerationCost.created_at >= since_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format")

    query = query.order_by(GenerationCost.created_at.desc()).limit(100)
    result = await db.execute(query)
    records = result.scalars().all()

    # Summary
    summary_query = select(
        GenerationCost.provider,
        GenerationCost.model,
        func.count(GenerationCost.id).label("count"),
        func.sum(GenerationCost.cost).label("total_cost"),
    ).group_by(GenerationCost.provider, GenerationCost.model)

    if provider:
        summary_query = summary_query.where(GenerationCost.provider == provider)
    if since:
        try:
            since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            summary_query = summary_query.where(GenerationCost.created_at >= since_dt)
        except ValueError:
            pass

    summary_result = await db.execute(summary_query)
    summaries = summary_result.all()

    return {
        "records": [
            {
                "id": r.id,
                "provider": r.provider,
                "model": r.model,
                "service_type": r.service_type,
                "cost": r.cost,
                "status": r.status,
                "task_id": r.task_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "summary": [
            {
                "provider": s.provider,
                "model": s.model,
                "count": s.count,
                "total_cost": float(s.total_cost or 0),
            }
            for s in summaries
        ],
    }
