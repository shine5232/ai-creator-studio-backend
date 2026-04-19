"""Celery tasks for knowledge-base video analysis."""

import json

from app.models.knowledge import KBCase, KBElement, KBFramework
from app.utils.logger import logger
from app.worker.celery_app import celery_app
from app.worker.db import get_sync_session


@celery_app.task(
    bind=True,
    name="app.worker.tasks.knowledge.analyze_video_task",
    soft_time_limit=600,
    time_limit=900,
)
def analyze_video_task(
    self,
    source_url: str,
    platform: str,
    case_id: int,
):
    """Download, extract frames and run GLM analysis on a video."""
    from app.services.video_analysis_service import VideoAnalysisService

    service = VideoAnalysisService()

    def update_progress(progress: int, message: str = ""):
        """Update KBCase progress directly."""
        self.update_state(state="PROGRESS", meta={"progress": progress, "message": message})
        try:
            with get_sync_session() as session:
                kb_case = session.get(KBCase, case_id)
                if kb_case:
                    kb_case.analysis_progress = progress
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

    try:
        result = service.analyze_video(
            source_url,
            platform,
            on_progress=update_progress,
        )

        # Persist results to KBCase
        with get_sync_session() as session:
            kb_case = session.get(KBCase, case_id)
            if kb_case:
                meta = result["metadata"]
                report = result["report"]

                kb_case.source_video_path = meta["video_path"]
                kb_case.title = meta["title"] or kb_case.title
                kb_case.duration_seconds = meta["duration"]
                kb_case.uploader = meta["uploader"]
                kb_case.upload_date = meta["upload_date"]
                kb_case.view_count = meta["view_count"]
                kb_case.like_count = meta["like_count"]
                kb_case.platform = meta["platform"]
                kb_case.frames_dir = str(result["work_dir"]) + "/frames"
                kb_case.analysis_report_path = result["report_path"]

                kb_case.theme = report.get("theme")
                kb_case.narrative_type = report.get("narrative_type")
                kb_case.narrative_structure = report.get("narrative_structure")
                kb_case.story_summary = report.get("story_summary")
                kb_case.emotion_curve = report.get("emotion_curve")
                kb_case.emotion_triggers = report.get("emotion_triggers")
                kb_case.visual_style = report.get("visual_style")
                kb_case.visual_contrast = report.get("visual_contrast")
                kb_case.viral_elements = _to_json(report.get("viral_elements"))
                kb_case.visual_symbols = _to_json(report.get("visual_symbols"))
                kb_case.audience_profile = report.get("audience_profile")
                kb_case.reusable_elements = _to_json(report.get("reusable_elements"))
                kb_case.success_factors = _to_json(report.get("success_factors"))
                kb_case.title_formula = report.get("title_formula")
                kb_case.characters_ethnicity = report.get("characters_ethnicity")

                kb_case.analysis_status = "completed"
                kb_case.analysis_progress = 100
                session.commit()

                # --- 拆分入库：viral_elements / visual_symbols → kb_elements ---
                _extract_elements(session, kb_case, report)

                # --- 提取叙事框架 → kb_frameworks ---
                _extract_framework(session, kb_case, report)

                session.commit()

        logger.info(f"Video analysis completed for case {case_id}")

    except Exception as e:
        logger.error(f"Video analysis failed for case {case_id}: {e}")
        # Mark as failed
        try:
            with get_sync_session() as session:
                kb_case = session.get(KBCase, case_id)
                if kb_case:
                    kb_case.analysis_status = "failed"
                    kb_case.analysis_report_path = f"ERROR: {e}"
                    session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update KBCase on failure: {db_exc}")
        raise


def _to_json(value) -> str | None:
    """Convert a list/dict to JSON string for Text columns."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)


def _extract_elements(session, kb_case: KBCase, report: dict):
    """拆分 viral_elements / visual_symbols → kb_elements，去重并累加 impact_score。"""
    # viral_elements - new format is a dict with topic_layer, emotion_layer, execution_layer
    viral_data = report.get("viral_elements", {})
    if isinstance(viral_data, dict):
        # Extract from each layer
        for layer_name, layer_list in viral_data.items():
            if isinstance(layer_list, list):
                for elem_name in layer_list:
                    if not elem_name or not isinstance(elem_name, str):
                        continue
                    existing = session.query(KBElement).filter_by(
                        name=elem_name, element_type=f"viral_{layer_name}"
                    ).first()
                    if existing:
                        existing.impact_score = (existing.impact_score or 0) + 1
                    else:
                        session.add(KBElement(
                            element_type=f"viral_{layer_name}",
                            name=elem_name,
                            description=f"来自案例 [{layer_name}]: {kb_case.title}",
                            impact_score=1.0,
                            examples=_to_json([kb_case.title]),
                        ))
    elif isinstance(viral_data, list):
        # Legacy format - list of strings
        for elem_name in viral_data:
            if not elem_name or not isinstance(elem_name, str):
                continue
            existing = session.query(KBElement).filter_by(name=elem_name).first()
            if existing:
                existing.impact_score = (existing.impact_score or 0) + 1
            else:
                session.add(KBElement(
                    element_type="viral",
                    name=elem_name,
                    description=f"来自案例: {kb_case.title}",
                    impact_score=1.0,
                    examples=_to_json([kb_case.title]),
                ))

    # visual_symbols - new format may include descriptions
    symbols_data = report.get("visual_symbols", [])
    if isinstance(symbols_data, list):
        for sym_data in symbols_data:
            if isinstance(sym_data, str):
                sym_name = sym_data
                sym_desc = f"来自案例: {kb_case.title}"
            elif isinstance(sym_data, dict):
                sym_name = sym_data.get("name", "")
                sym_desc = sym_data.get("meaning", f"来自案例: {kb_case.title}")
            else:
                continue

            if not sym_name:
                continue
            existing = session.query(KBElement).filter_by(name=sym_name).first()
            if existing:
                existing.impact_score = (existing.impact_score or 0) + 1
            else:
                session.add(KBElement(
                    element_type="visual_symbol",
                    name=sym_name,
                    description=sym_desc,
                    impact_score=1.0,
                    examples=_to_json([kb_case.title]),
                ))


def _extract_framework(session, kb_case: KBCase, report: dict):
    """提取叙事框架 → kb_frameworks，累加统计数据。"""
    narrative = report.get("narrative_type")
    if not narrative:
        return
    existing_fw = session.query(KBFramework).filter_by(name=narrative).first()
    if existing_fw:
        data = json.loads(existing_fw.impact_data) if existing_fw.impact_data else {}
        data["total_cases"] = data.get("total_cases", 0) + 1
        data["avg_like_rate"] = (
            (data.get("avg_like_rate", 0) * (data["total_cases"] - 1) + (kb_case.like_rate or 0))
            / data["total_cases"]
        )
        existing_fw.impact_data = _to_json(data)
        examples = json.loads(existing_fw.examples) if existing_fw.examples else []
        if kb_case.title not in examples:
            examples.append(kb_case.title)
        existing_fw.examples = _to_json(examples)
    else:
        session.add(KBFramework(
            framework_type="narrative",
            name=narrative,
            description=f"叙事类型: {narrative}",
            formula=report.get("emotion_curve", ""),
            impact_data=_to_json({"total_cases": 1, "avg_like_rate": kb_case.like_rate or 0}),
            examples=_to_json([kb_case.title]),
        ))
