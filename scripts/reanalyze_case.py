"""直接调用重新分析逻辑，绕过 API 认证。"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from app.services.video_analysis_service import VideoAnalysisService
from app.worker.db import get_sync_session
from app.worker.tasks.knowledge import _to_json, _extract_elements, _extract_framework
from app.models.knowledge import KBCase

CASE_ID = 1


def main():
    service = VideoAnalysisService()

    def update_progress(progress: int, message: str = ""):
        progress = int(progress)
        print(f"[{progress}%] {message}")
        try:
            with get_sync_session() as session:
                kb_case = session.get(KBCase, CASE_ID)
                if kb_case:
                    kb_case.analysis_progress = progress
                    session.commit()
        except Exception as e:
            print(f"Progress update error: {e}")

    # 1. 读取案例信息
    print(f"Reading case {CASE_ID}...")
    with get_sync_session() as session:
        kb_case = session.get(KBCase, CASE_ID)
        if not kb_case:
            print(f"Case {CASE_ID} not found!")
            return
        if not kb_case.frames_dir:
            print(f"Case {CASE_ID} has no frames_dir!")
            return

        # 重置状态
        kb_case.analysis_status = "processing"
        kb_case.analysis_progress = 0
        session.commit()

        work_dir = str(Path(kb_case.frames_dir).parent)
        metadata = {
            "video_path": kb_case.source_video_path or "",
            "title": kb_case.title or "",
            "duration": kb_case.duration_seconds or 0,
            "uploader": kb_case.uploader or "",
            "upload_date": kb_case.upload_date or "",
            "view_count": kb_case.view_count,
            "like_count": kb_case.like_count,
            "description": "",
            "platform": kb_case.platform or "",
            "work_dir": work_dir,
        }

    print(f"Work dir: {work_dir}")
    frames_dir = Path(work_dir) / "frames"
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"Found {len(frames)} frames")

    # 2. 执行重新分析
    result = service.reanalyze_video(work_dir, metadata, on_progress=update_progress)

    # 3. 保存结果
    print("Saving results...")
    with get_sync_session() as session:
        kb_case = session.get(KBCase, CASE_ID)
        if kb_case:
            report = result["report"]

            kb_case.analysis_report_path = result["report_path"]
            kb_case.theme = _to_json(report.get("theme"))
            kb_case.narrative_type = _to_json(report.get("narrative_type"))
            kb_case.narrative_structure = _to_json(report.get("narrative_structure"))
            kb_case.story_summary = _to_json(report.get("story_summary"))
            kb_case.emotion_curve = _to_json(report.get("emotion_curve"))
            kb_case.emotion_triggers = _to_json(report.get("emotion_triggers"))
            kb_case.visual_style = _to_json(report.get("visual_style"))
            kb_case.visual_contrast = _to_json(report.get("visual_contrast"))
            kb_case.viral_elements = _to_json(report.get("viral_elements"))
            kb_case.visual_symbols = _to_json(report.get("visual_symbols"))
            kb_case.audience_profile = _to_json(report.get("audience_profile"))
            kb_case.reusable_elements = _to_json(report.get("reusable_elements"))
            kb_case.success_factors = _to_json(report.get("success_factors"))
            kb_case.title_formula = _to_json(report.get("title_formula"))
            kb_case.characters_ethnicity = _to_json(report.get("characters_ethnicity"))

            kb_case.analysis_status = "completed"
            kb_case.analysis_progress = 100
            session.commit()

            _extract_elements(session, kb_case, report)
            _extract_framework(session, kb_case, report)
            session.commit()

    print("Done!")


if __name__ == "__main__":
    main()
