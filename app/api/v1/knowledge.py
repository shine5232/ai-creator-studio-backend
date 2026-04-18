from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.knowledge import (
    AnalyzeVideoRequest, KBCaseResponse, KBElementResponse, KBFrameworkResponse,
    KBReferenceContext, KBScriptTemplateResponse, RecommendThemesRequest, SearchKnowledgeRequest,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@router.get("/cases")
async def list_cases(
    request: Request,
    platform: str | None = None,
    theme: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    cases, total = await service.list_cases(platform, theme, page, page_size)
    base = str(request.base_url).rstrip("/")
    items = []
    for c in cases:
        data = KBCaseResponse.model_validate(c).model_dump()
        if data.get("thumbnail_url"):
            data["thumbnail_url"] = base + data["thumbnail_url"]
        items.append(data)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    deleted = await service.delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"detail": "Deleted"}


@router.get("/cases/{case_id}")
async def get_case(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    case = await service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    data = KBCaseResponse.model_validate(case).model_dump()
    if data.get("thumbnail_url"):
        base = str(request.base_url).rstrip("/")
        data["thumbnail_url"] = base + data["thumbnail_url"]
    return data


@router.get("/cases/{case_id}/thumbnail")
async def get_case_thumbnail(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Serve the first extracted frame as case thumbnail (no auth required for image loading)."""
    service = KnowledgeService(db)
    case = await service.get_case(case_id)
    if not case or not case.frames_dir:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    thumb = Path(case.frames_dir) / "frame_002.jpg"
    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")

    return FileResponse(thumb, media_type="image/jpeg")


@router.get("/elements")
async def list_elements(
    element_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    elements = await service.list_elements(element_type)
    return [KBElementResponse.model_validate(e).model_dump() for e in elements]


@router.get("/frameworks")
async def list_frameworks(
    framework_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    frameworks = await service.list_frameworks(framework_type)
    return [KBFrameworkResponse.model_validate(f).model_dump() for f in frameworks]


@router.get("/script-templates")
async def list_script_templates(
    theme: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    templates = await service.list_script_templates(theme)
    return [KBScriptTemplateResponse.model_validate(t).model_dump() for t in templates]


@router.post("/analyze-video")
async def analyze_video(
    data: AnalyzeVideoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    return await service.analyze_video(data.source_url, data.platform)


@router.get("/analysis/{case_id}")
async def get_analysis_status(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query analysis progress and results for a given KBCase."""
    from app.models.knowledge import KBCase
    from app.models.project import WorkflowStep

    service = KnowledgeService(db)
    case = await service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    result = {
        "case_id": case.id,
        "analysis_status": case.analysis_status,
        "title": case.title,
    }

    # Include progress from WorkflowStep if available
    if case.celery_task_id:
        from sqlalchemy import select as sa_select
        step_result = await db.execute(
            sa_select(WorkflowStep).where(
                WorkflowStep.celery_task_id == case.celery_task_id
            )
        )
        step = step_result.scalar_one_or_none()
        if step:
            result["progress"] = step.progress
            result["step_status"] = step.status
            result["error_message"] = step.error_message

    # Include analysis results if completed
    if case.analysis_status == "completed":
        result.update({
            "theme": case.theme,
            "narrative_type": case.narrative_type,
            "emotion_curve": case.emotion_curve,
            "visual_style": case.visual_style,
            "viral_elements": case.viral_elements,
            "visual_symbols": case.visual_symbols,
            "title_formula": case.title_formula,
            "characters_ethnicity": case.characters_ethnicity,
            "report_path": case.analysis_report_path,
            "duration_seconds": case.duration_seconds,
            "view_count": case.view_count,
            "like_count": case.like_count,
        })

    return result


@router.post("/search")
async def search_knowledge(
    data: SearchKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    return await service.search(data.query, data.element_type, data.limit)


@router.post("/recommend-themes")
async def recommend_themes(
    data: RecommendThemesRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    cases = await service.recommend_themes(data.description, data.platform, data.limit)
    base = str(request.base_url).rstrip("/")
    results = []
    for c in cases:
        d = KBCaseResponse.model_validate(c).model_dump()
        if d.get("thumbnail_url"):
            d["thumbnail_url"] = base + d["thumbnail_url"]
        results.append(d)
    return results


@router.post("/recommend-cases")
async def recommend_cases(
    data: RecommendThemesRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """推荐最佳参考案例（仅返回已完成分析的），供前端在创建项目时选择。"""
    service = KnowledgeService(db)
    cases = await service.recommend_cases_for_project(
        description=data.description,
        platform=data.platform,
        limit=data.limit,
    )
    base = str(request.base_url).rstrip("/")
    results = []
    for c in cases:
        d = KBCaseResponse.model_validate(c).model_dump()
        if d.get("thumbnail_url"):
            d["thumbnail_url"] = base + d["thumbnail_url"]
        results.append(d)
    return results


@router.post("/cases/{case_id}/generate-template")
async def generate_template(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从已分析案例自动生成脚本模板。"""
    service = KnowledgeService(db)
    template = await service.generate_script_template(case_id)
    if not template:
        raise HTTPException(status_code=404, detail="Case not found or not analyzed")
    return KBScriptTemplateResponse.model_validate(template).model_dump()


@router.get("/cases/{case_id}/reference-context", response_model=KBReferenceContext)
async def get_reference_context(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取案例的完整参考上下文，供创作流程使用。"""
    service = KnowledgeService(db)
    ctx = await service.get_reference_context(case_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Case not found or not analyzed")
    return ctx
