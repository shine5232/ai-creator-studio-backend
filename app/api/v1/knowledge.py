import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.config import settings
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge import KBCase
from app.schemas.knowledge import (
    AnalyzeVideoRequest, KBCaseResponse, KBElementResponse, KBFrameworkResponse,
    KBReferenceContext, KBScriptTemplateResponse, RecommendThemesRequest, SearchKnowledgeRequest,
)
from app.services.knowledge_service import KnowledgeService
from app.utils.logger import logger

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


# 测试端点 - 验证后端是否正常工作
@router.get("/test-db")
async def test_database(db: AsyncSession = Depends(get_db)):
    """测试数据库连接和内容（无需认证）"""
    count_result = await db.execute(select(func.count(KBCase.id)))
    total_count = count_result.scalar()

    all_ids_result = await db.execute(select(KBCase.id))
    all_ids = list(all_ids_result.scalars().all())

    return {
        "database": settings.DATABASE_URL,
        "total_cases": total_count,
        "case_ids": all_ids
    }


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
    service = KnowledgeService(db)
    case = await service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    result = {
        "case_id": case.id,
        "analysis_status": case.analysis_status,
        "analysis_progress": case.analysis_progress or 0,
        "title": case.title,
    }

    # Include analysis results if completed
    if case.analysis_status == "completed":
        result.update({
            "theme": case.theme,
            "narrative_type": case.narrative_type,
            "narrative_structure": case.narrative_structure,
            "story_summary": case.story_summary,
            "emotion_curve": case.emotion_curve,
            "emotion_triggers": case.emotion_triggers,
            "visual_style": case.visual_style,
            "visual_contrast": case.visual_contrast,
            "viral_elements": case.viral_elements,
            "visual_symbols": case.visual_symbols,
            "audience_profile": case.audience_profile,
            "reusable_elements": case.reusable_elements,
            "success_factors": case.success_factors,
            "title_formula": case.title_formula,
            "characters_ethnicity": case.characters_ethnicity,
            "report_path": case.analysis_report_path,
            "duration_seconds": case.duration_seconds,
            "view_count": case.view_count,
            "like_count": case.like_count,
        })

    # Include error message if failed
    if case.analysis_status == "failed" and case.analysis_report_path:
        result["error_message"] = case.analysis_report_path

    return result


@router.post("/cases/{case_id}/reanalyze")
async def reanalyze_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-analyze an existing case using its extracted frames."""
    service = KnowledgeService(db)
    case = await service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.frames_dir:
        raise HTTPException(status_code=400, detail="Case has no extracted frames, cannot reanalyze")

    # Reset status
    case.analysis_status = "pending"
    case.analysis_progress = 0
    await db.commit()

    # Dispatch Celery task
    from app.worker.tasks.knowledge import reanalyze_video_task
    celery_result = reanalyze_video_task.delay(case_id=case_id)

    # Save task id
    case.celery_task_id = celery_result.id
    await db.commit()

    logger.info(f"Re-analysis task submitted: case={case_id}, task={celery_result.id}")

    return {
        "case_id": case_id,
        "task_id": celery_result.id,
        "status": "pending",
    }


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


@router.get("/cases/{case_id}/markdown")
async def get_case_markdown(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取案例的 Markdown 分析报告"""
    # 调试：检查数据库中的案例数量
    count_result = await db.execute(select(func.count(KBCase.id)))
    total_count = count_result.scalar()
    logger.info(f"[DEBUG] Total cases in DB: {total_count}")

    # 列出所有案例 ID
    all_ids_result = await db.execute(select(KBCase.id))
    all_ids = all_ids_result.scalars().all()
    logger.info(f"[DEBUG] All case IDs: {list(all_ids)}")

    service = KnowledgeService(db)
    case = await service.get_case(case_id)

    logger.info(f"[DEBUG] Requested case_id={case_id}, case_found={case is not None}")

    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found. Available IDs: {list(all_ids)}")

    if not case.analysis_report_path:
        raise HTTPException(status_code=404, detail="Analysis report not found")

    # Try markdown file first, fall back to json
    report_path = Path(case.analysis_report_path)
    md_path = report_path.parent / "report.md"

    logger.info(f"[DEBUG] report_path exists={report_path.exists()}, md_exists={md_path.exists()}")

    if md_path.exists():
        return FileResponse(
            md_path,
            media_type="text/markdown",
            filename="report.md",
        )
    elif report_path.exists():
        # Fallback: if only json exists, convert it on the fly
        data = json.loads(report_path.read_text(encoding="utf-8"))
        markdown = service._json_to_markdown(data)
        return Response(content=markdown, media_type="text/markdown")
    else:
        raise HTTPException(status_code=404, detail="Analysis report file not found on disk")
