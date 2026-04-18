"""Video analysis service: download → extract frames → GLM vision analysis."""

import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Callable

from app.config import settings
from app.utils.logger import logger


class VideoAnalysisService:
    """Synchronous service intended to run inside a Celery worker."""

    # ── public entry point ────────────────────────────────────────────────────

    def analyze_video(
        self,
        source_url: str,
        platform: str,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> dict:
        """Full pipeline: download → frames → describe → structural analysis.

        Returns a dict with metadata, analysis results and file paths.
        """
        on_progress = on_progress or (lambda p, m: None)
        on_progress(5, "Initializing...")

        # 1. Download
        work_dir: Path | None = None
        try:
            video_info = self.download_video(source_url, settings.ANALYSIS_BASE_DIR, platform)
            work_dir = Path(video_info["video_path"]).parent
            on_progress(20, "Video downloaded")

            # 2. Extract frames
            frames_dir = work_dir / "frames"
            frame_paths = self.extract_frames(
                video_info["video_path"],
                str(frames_dir),
                interval_seconds=settings.ANALYSIS_FRAME_INTERVAL,
            )
            on_progress(40, f"Extracted {len(frame_paths)} frames")

            # 3. Describe frames with GLM-4.6V-Flash
            descriptions = self.describe_frames(frame_paths)
            on_progress(60, "Frame descriptions complete")

            # 4. Structural analysis
            report = self.analyze_content(video_info, descriptions)
            on_progress(85, "Structural analysis complete")

            # 5. Save report
            report_path = work_dir / "report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            on_progress(100, "Done")

            return {
                "metadata": video_info,
                "frame_paths": frame_paths,
                "report": report,
                "work_dir": str(work_dir),
                "report_path": str(report_path),
            }
        except Exception:
            # Clean up partial downloads on failure
            raise

    # ── download ──────────────────────────────────────────────────────────────

    def download_video(self, source_url: str, base_dir: str, platform: str = "") -> dict:
        """Download video via yt-dlp. Returns metadata dict."""
        import yt_dlp

        out_dir = Path(base_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "best[height<=720][filesize<500M]/best[height<=720]",
            "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 3,
        }

        # Attach cookie file if available
        if platform:
            cookie_file = Path("data/cookies") / f"{platform}.txt"
            if cookie_file.exists():
                ydl_opts["cookiefile"] = str(cookie_file)
                logger.info(f"Using cookie file for {platform}: {cookie_file}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            video_path = ydl.prepare_filename(info)
            # yt-dlp may change extension (e.g. webm → mkv), check actual
            if not Path(video_path).exists():
                # Try to find the actual file
                stem = Path(video_path).stem
                candidates = list(out_dir.glob(f"{stem}.*"))
                if candidates:
                    video_path = str(candidates[0])

        duration = info.get("duration") or 0
        if duration > settings.ANALYSIS_MAX_DURATION:
            # Remove downloaded file
            Path(video_path).unlink(missing_ok=True)
            raise ValueError(
                f"Video too long: {duration:.0f}s > {settings.ANALYSIS_MAX_DURATION}s limit"
            )

        return {
            "video_path": video_path,
            "title": info.get("title", ""),
            "duration": int(duration),
            "uploader": info.get("uploader") or info.get("channel", ""),
            "upload_date": info.get("upload_date", ""),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "description": info.get("description") or "",
            "platform": info.get("extractor_key", platform).lower(),
        }

    # ── frame extraction ──────────────────────────────────────────────────────

    def extract_frames(self, video_path: str, output_dir: str, interval_seconds: int = 3) -> list[str]:
        """Extract one JPEG frame every *interval_seconds* via ffmpeg/ffprobe."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Get duration via ffprobe
        probe = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if probe.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {probe.stderr.strip()}")

        duration = float(probe.stdout.strip())
        if duration <= 0:
            raise RuntimeError(f"Invalid video duration: {duration}")

        frame_paths: list[str] = []
        timestamp = interval_seconds
        idx = 1
        while timestamp < duration:
            out_path = out / f"frame_{idx:03d}.jpg"
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", f"{timestamp:.3f}",
                    "-i", video_path,
                    "-frames:v", "1",
                    "-q:v", "2",
                    str(out_path),
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and out_path.exists():
                frame_paths.append(str(out_path))
            else:
                logger.warning(f"Failed to extract frame at {timestamp:.1f}s: {result.stderr.strip()[:200]}")
            timestamp += interval_seconds
            idx += 1

        if not frame_paths:
            raise RuntimeError("All frame extractions failed")

        return frame_paths

    # ── GLM-4.6V-Flash frame description ──────────────────────────────────────

    def describe_frames(self, frame_paths: list[str]) -> list[str]:
        """Use GLM-4.6V-Flash to describe each frame."""
        from zai import ZhipuAiClient

        client = ZhipuAiClient(api_key=settings.ZHIPU_API_KEY)
        descriptions: list[str] = []

        for path in frame_paths:
            img_b64 = base64.b64encode(Path(path).read_bytes()).decode()
            try:
                resp = client.chat.completions.create(
                    model="glm-4.6v-flash",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": img_b64},
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "请详细描述这个视频帧的画面内容，包括：人物外貌和表情、"
                                        "场景和背景、色调和光影、文字或标志、整体氛围。用中文回答。"
                                    ),
                                },
                            ],
                        }
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                descriptions.append(resp.choices[0].message.content)
            except Exception as e:
                logger.error(f"GLM-4.6V-Flash frame description failed for {path}: {e}")
                descriptions.append(f"[描述失败: {e}]")

        return descriptions

    # ── structural analysis ───────────────────────────────────────────────────

    def analyze_content(self, metadata: dict, frame_descriptions: list[str]) -> dict:
        """Use GLM-4-Flash to produce structured analysis JSON."""
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)

        meta_text = (
            f"标题: {metadata['title']}\n"
            f"时长: {metadata['duration']}秒\n"
            f"上传者: {metadata['uploader']}\n"
            f"播放量: {metadata['view_count']}\n"
            f"点赞数: {metadata['like_count']}\n"
            f"描述: {metadata['description'][:500]}\n"
        )
        frames_text = "\n".join(
            f"帧{i+1}: {d}" for i, d in enumerate(frame_descriptions)
        )

        prompt = (
            "你是一个专业的短视频分析师。请根据以下视频元数据和关键帧描述，"
            "输出一份 JSON 格式的分析报告。\n\n"
            f"【视频元数据】\n{meta_text}\n"
            f"【关键帧描述】\n{frames_text}\n\n"
            "请输出严格符合以下结构的 JSON（不要包含任何其他文字）：\n"
            "```json\n"
            "{\n"
            '  "theme": "视频主题（如：励志、搞笑、情感等）",\n'
            '  "narrative_type": "叙事类型（如：反转、递进、并列、情感共鸣等）",\n'
            '  "story_summary": "用500-1000字非常详细地描述整个视频的故事情节，包括：开头场景的具体内容、人物的动作和表情、情节发展的每个阶段、关键转折点的细节、高潮部分的画面和氛围、结局的呈现方式。请按时间线逐段描述，不要遗漏重要细节",\n'
            '  "emotion_curve": "情感曲线描述（如：平静→悬念→高潮→感动）",\n'
            '  "visual_style": "视觉风格描述",\n'
            '  "viral_elements": ["爆点要素1", "爆点要素2"],\n'
            '  "visual_symbols": ["视觉符号1", "视觉符号2"],\n'
            '  "title_formula": "标题公式/套路总结",\n'
            '  "characters_ethnicity": "人物外貌/种族描述"\n'
            "}\n"
            "```\n"
        )

        try:
            resp = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000,
            )
            text = resp.choices[0].message.content
            return self._parse_json_response(text)
        except Exception as e:
            logger.error(f"Structural analysis failed: {e}")
            return self._default_report()

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Extract JSON from LLM response, handling markdown fences."""
        # Try to extract JSON block from markdown code fences
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        json_str = m.group(1).strip() if m else text.strip()
        try:
            return json.loads(json_str, strict=False)
        except json.JSONDecodeError:
            # Try to find first { ... } block
            m2 = re.search(r"\{.*\}", json_str, re.DOTALL)
            if m2:
                try:
                    return json.loads(m2.group(), strict=False)
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse JSON response: {text[:200]}")
            return VideoAnalysisService._default_report()

    @staticmethod
    def _default_report() -> dict:
        return {
            "theme": "",
            "narrative_type": "",
            "story_summary": "",
            "emotion_curve": "",
            "visual_style": "",
            "viral_elements": [],
            "visual_symbols": [],
            "title_formula": "",
            "characters_ethnicity": "",
        }
