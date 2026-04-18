import json

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KBCase, KBElement, KBFramework, KBScriptTemplate
from app.utils.logger import logger


def _to_json(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cases(
        self, platform: str | None = None, theme: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[KBCase], int]:
        query = select(KBCase)
        if platform:
            query = query.where(KBCase.platform == platform)
        if theme:
            query = query.where(KBCase.theme == theme)

        total_result = await self.db.execute(query)
        total = len(total_result.scalars().all())

        result = await self.db.execute(
            query.order_by(KBCase.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total

    async def get_case(self, case_id: int) -> KBCase | None:
        result = await self.db.execute(select(KBCase).where(KBCase.id == case_id))
        return result.scalar_one_or_none()

    async def delete_case(self, case_id: int) -> bool:
        case = await self.get_case(case_id)
        if not case:
            return False
        # Clean up associated files
        if case.frames_dir:
            from pathlib import Path, shutil
            frames_path = Path(case.frames_dir)
            if frames_path.exists():
                shutil.rmtree(frames_path, ignore_errors=True)
        if case.analysis_report_path:
            from pathlib import Path
            report_path = Path(case.analysis_report_path)
            if report_path.exists():
                report_path.unlink(missing_ok=True)
        await self.db.delete(case)
        await self.db.commit()
        return True

    async def list_elements(self, element_type: str | None = None) -> list[KBElement]:
        query = select(KBElement)
        if element_type:
            query = query.where(KBElement.element_type == element_type)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_frameworks(self, framework_type: str | None = None) -> list[KBFramework]:
        query = select(KBFramework)
        if framework_type:
            query = query.where(KBFramework.framework_type == framework_type)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_script_templates(self, theme: str | None = None) -> list[KBScriptTemplate]:
        query = select(KBScriptTemplate)
        if theme:
            query = query.where(KBScriptTemplate.theme == theme)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def analyze_video(self, source_url: str, platform: str) -> dict:
        """Submit a video analysis task. Creates KBCase, then dispatches Celery task."""
        from app.models.knowledge import KBCase

        # Create KBCase record
        kb_case = KBCase(
            platform=platform,
            title=source_url[:200],
            source_url=source_url,
            analysis_status="pending",
        )
        self.db.add(kb_case)
        await self.db.commit()
        await self.db.refresh(kb_case)

        # Dispatch Celery task
        from app.worker.tasks.knowledge import analyze_video_task

        celery_result = analyze_video_task.delay(
            source_url=source_url,
            platform=platform,
            case_id=kb_case.id,
        )

        # Save celery_task_id back to KBCase
        kb_case.celery_task_id = celery_result.id
        await self.db.commit()

        logger.info(f"Video analysis task submitted: case={kb_case.id}, task={celery_result.id}")

        return {
            "case_id": kb_case.id,
            "task_id": celery_result.id,
            "status": "pending",
        }

    async def search(self, query: str, element_type: str | None = None, limit: int = 20) -> dict:
        """Search across knowledge base."""
        results = {}

        # Search cases
        case_query = select(KBCase).where(
            or_(
                KBCase.title.contains(query),
                KBCase.theme.contains(query),
            )
        ).limit(limit)
        case_result = await self.db.execute(case_query)
        results["cases"] = case_result.scalars().all()

        # Search elements
        elem_query = select(KBElement).where(
            or_(
                KBElement.name.contains(query),
                KBElement.description.contains(query),
            )
        )
        if element_type:
            elem_query = elem_query.where(KBElement.element_type == element_type)
        elem_query = elem_query.limit(limit)
        elem_result = await self.db.execute(elem_query)
        results["elements"] = elem_result.scalars().all()

        return results

    async def recommend_themes(self, description: str | None = None, platform: str | None = None, limit: int = 10) -> list[KBCase]:
        """Recommend themes based on description. Returns top cases."""
        query = select(KBCase).order_by(KBCase.like_rate.desc().nullslast())
        if platform:
            query = query.where(KBCase.platform == platform)
        query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # 知识库闭环：参考上下文 / 脚本模板生成 / 案例推荐
    # ------------------------------------------------------------------

    async def get_reference_context(self, case_id: int) -> dict | None:
        """获取单个案例的完整参考上下文，供创作流程使用。"""
        case = await self.get_case(case_id)
        if not case or case.analysis_status != "completed":
            return None
        viral = json.loads(case.viral_elements) if case.viral_elements else []
        symbols = json.loads(case.visual_symbols) if case.visual_symbols else []
        return {
            "case_id": case.id,
            "title": case.title,
            "theme": case.theme,
            "narrative_type": case.narrative_type,
            "story_summary": case.story_summary,
            "emotion_curve": case.emotion_curve,
            "visual_style": case.visual_style,
            "viral_elements": viral,
            "visual_symbols": symbols,
            "title_formula": case.title_formula,
            "characters_ethnicity": case.characters_ethnicity,
            "like_rate": case.like_rate,
        }

    async def generate_script_template(self, case_id: int) -> KBScriptTemplate | None:
        """从已分析案例自动生成脚本模板，存入 kb_script_templates。"""
        ctx = await self.get_reference_context(case_id)
        if not ctx:
            return None
        template = KBScriptTemplate(
            name=f"模板-{ctx['title'][:50]}",
            theme=ctx["theme"],
            narrative_type=ctx["narrative_type"],
            template_content=_to_json(ctx),
            reference_case_id=case_id,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def recommend_cases_for_project(
        self, description: str | None = None, platform: str | None = None, limit: int = 5,
    ) -> list[KBCase]:
        """基于项目描述推荐最佳参考案例（按 like_rate 排序）。"""
        query = select(KBCase).where(KBCase.analysis_status == "completed")
        if platform:
            query = query.where(KBCase.platform == platform)
        query = query.order_by(KBCase.like_rate.desc().nullslast()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
