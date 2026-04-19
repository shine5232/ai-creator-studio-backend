"""Video analysis service: download → extract frames → GLM vision analysis.

Retry Configuration:
- Frame description: 3 retries, 2s exponential backoff, 60s timeout
- Structural analysis: 3 retries, 3s exponential backoff, 120s timeout
- Frame extraction: 2 retries per frame, 1s delay, 30s timeout
"""

import base64
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from app.config import settings
from app.utils.logger import logger

# Retry configuration constants
FRAME_DESC_MAX_RETRIES = 3
FRAME_DESC_RETRY_DELAY = 2  # seconds
FRAME_DESC_TIMEOUT = 60  # seconds

STRUCTURAL_MAX_RETRIES = 3
STRUCTURAL_RETRY_DELAY = 3  # seconds
STRUCTURAL_TIMEOUT = 120  # seconds

FRAME_EXTRACT_MAX_RETRIES = 2
FRAME_EXTRACT_RETRY_DELAY = 1  # seconds
FRAME_EXTRACT_TIMEOUT = 30  # seconds


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a filename by removing invalid characters and limiting length."""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', '_', name)
    # Remove leading/trailing spaces and dots
    name = name.strip('. ')
    # Limit length
    if len(name) > max_length:
        name = name[:max_length].rsplit('_', 1)[0]
    return name or "untitled"


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
            work_dir = Path(video_info["work_dir"])
            on_progress(20, f"Video downloaded to {work_dir}")

            # 2. Extract frames
            frames_dir = work_dir / "frames"
            frame_paths = self.extract_frames(
                video_info["video_path"],
                str(frames_dir),
                interval_seconds=settings.ANALYSIS_FRAME_INTERVAL,
                on_progress=lambda p, m: on_progress(20 + p * 0.2, m),  # 20% -> 40%
            )
            on_progress(40, f"Extracted {len(frame_paths)} frames")

            # 3. Describe frames with GLM-4.6V-Flash
            descriptions = self.describe_frames(
                frame_paths,
                on_progress=lambda p, m: on_progress(40 + p * 0.2, m),  # 40% -> 60%
            )
            on_progress(60, "Frame descriptions complete")

            # 4. Structural analysis
            report = self.analyze_content(video_info, descriptions)
            on_progress(85, "Structural analysis complete")

            # 5. Save report (both JSON and Markdown)
            report_path = work_dir / "report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            markdown_path = work_dir / "report.md"
            markdown_content = self._generate_markdown_report(video_info, descriptions, report)
            markdown_path.write_text(markdown_content, encoding="utf-8")

            on_progress(100, "Done")

            return {
                "metadata": video_info,
                "frame_paths": frame_paths,
                "report": report,
                "work_dir": str(work_dir),
                "report_path": str(report_path),
                "markdown_path": str(markdown_path),
            }
        except Exception:
            # Clean up partial downloads on failure
            raise

    # ── reanalyze (skip download & frame extraction) ─────────────────────────

    def reanalyze_video(
        self,
        work_dir: str,
        metadata: dict,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> dict:
        """Re-analyze a video using existing frames only (no download/extract).

        Args:
            work_dir: The work directory containing frames/ subdirectory.
            metadata: Existing metadata dict with title, duration, etc.
            on_progress: Progress callback (0-100).

        Returns:
            Same structure as analyze_video().
        """
        on_progress = on_progress or (lambda p, m: None)
        on_progress(5, "Reading existing frames...")

        frames_dir = Path(work_dir) / "frames"
        frame_paths = sorted(str(p) for p in frames_dir.glob("frame_*.jpg"))
        if not frame_paths:
            raise FileNotFoundError(f"No frame images found in {frames_dir}")

        on_progress(10, f"Found {len(frame_paths)} existing frames")

        # Describe frames with GLM-4.6V-Flash (10% -> 50%)
        descriptions = self.describe_frames(
            frame_paths,
            on_progress=lambda p, m: on_progress(10 + p * 0.4, m),
        )
        on_progress(50, "Frame descriptions complete")

        # Structural analysis (50% -> 85%)
        report = self.analyze_content(metadata, descriptions)
        on_progress(85, "Structural analysis complete")

        # Save report (both JSON and Markdown)
        work_path = Path(work_dir)
        report_path = work_path / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        markdown_content = self._generate_markdown_report(metadata, descriptions, report)
        markdown_path = work_path / "report.md"
        markdown_path.write_text(markdown_content, encoding="utf-8")

        on_progress(100, "Done")

        return {
            "metadata": metadata,
            "frame_paths": frame_paths,
            "report": report,
            "work_dir": str(work_path),
            "report_path": str(report_path),
            "markdown_path": str(markdown_path),
        }

    # ── download ──────────────────────────────────────────────────────────────

    def download_video(self, source_url: str, base_dir: str, platform: str = "") -> dict:
        """Download video via yt-dlp. Returns metadata dict.

        Directory structure:
        {base_dir}/{platform}/{sanitized_title}/
            ├── {video_id}.ext          (video file)
            ├── frames/                 (extracted frames)
            │   ├── frame_001.jpg
            │   └── ...
            └── report.json            (analysis report)
        """
        import yt_dlp

        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # First, fetch video info without downloading to get title and platform
        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "skip_download": True,
        }

        # Attach cookie file if available
        if platform:
            cookie_file = Path("data/cookies") / f"{platform}.txt"
            if cookie_file.exists():
                info_opts["cookiefile"] = str(cookie_file)

        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(source_url, download=False)
            title = info.get("title", "untitled")
            video_id = info.get("id", "unknown")
            detected_platform = info.get("extractor_key", platform).lower()

        # Create directory structure: {base_dir}/{platform}/{sanitized_title}/
        sanitized_title = sanitize_filename(title)
        work_dir = base_path / detected_platform / sanitized_title
        work_dir.mkdir(parents=True, exist_ok=True)

        # Now download the video into the work directory
        download_opts = {
            "format": "best[height<=720][filesize<500M]/best[height<=720]",
            "outtmpl": str(work_dir / f"{video_id}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 3,
        }

        # Attach cookie file if available
        if platform:
            cookie_file = Path("data/cookies") / f"{platform}.txt"
            if cookie_file.exists():
                download_opts["cookiefile"] = str(cookie_file)

        with yt_dlp.YoutubeDL(download_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            video_path = ydl.prepare_filename(info)
            # yt-dlp may change extension (e.g. webm → mkv), check actual
            if not Path(video_path).exists():
                # Try to find the actual file
                stem = Path(video_path).stem
                candidates = list(work_dir.glob(f"{stem}.*"))
                if candidates:
                    video_path = str(candidates[0])

        duration = info.get("duration") or 0
        if duration > settings.ANALYSIS_MAX_DURATION:
            # Remove downloaded file and directory
            Path(video_path).unlink(missing_ok=True)
            if work_dir.exists():
                import shutil
                shutil.rmtree(work_dir, ignore_errors=True)
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
            "platform": detected_platform,
            "work_dir": str(work_dir),
        }

    # ── frame extraction ──────────────────────────────────────────────────────

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        interval_seconds: int = 3,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> list[str]:
        """Extract one JPEG frame every *interval_seconds* via ffmpeg/ffprobe with retry mechanism."""
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

        # Estimate total frames
        estimated_total = int(duration / interval_seconds)
        frame_paths: list[str] = []
        timestamp = interval_seconds
        idx = 1
        on_progress = on_progress or (lambda p, m: None)

        while timestamp < duration:
            out_path = out / f"frame_{idx:03d}.jpg"

            # Retry loop for frame extraction
            extracted = False
            for attempt in range(FRAME_EXTRACT_MAX_RETRIES):
                result = subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-ss", f"{timestamp:.3f}",
                        "-i", video_path,
                        "-frames:v", "1",
                        "-q:v", "2",
                        str(out_path),
                    ],
                    capture_output=True, text=True, timeout=FRAME_EXTRACT_TIMEOUT,
                )
                if result.returncode == 0 and out_path.exists():
                    frame_paths.append(str(out_path))
                    extracted = True
                    break
                else:
                    logger.warning(f"Frame extraction attempt {attempt + 1} failed at {timestamp:.1f}s")
                    if attempt < FRAME_EXTRACT_MAX_RETRIES - 1:
                        time.sleep(FRAME_EXTRACT_RETRY_DELAY)  # Brief delay before retry

            if not extracted:
                logger.warning(f"Failed to extract frame at {timestamp:.1f}s: {result.stderr.strip()[:200]}")

            # Update progress after each frame extraction attempt
            if estimated_total > 0:
                progress = int((idx / estimated_total) * 100)
                on_progress(progress, f"Extracting frame {idx}/{estimated_total}")

            timestamp += interval_seconds
            idx += 1

        if not frame_paths:
            raise RuntimeError("All frame extractions failed")

        logger.info(f"Successfully extracted {len(frame_paths)}/{idx - 1} frames")
        return frame_paths

    # ── Qwen 3.5 Plus frame description ──────────────────────────────────────

    @staticmethod
    def _get_qwen_client():
        from openai import OpenAI
        return OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def describe_frames(
        self,
        frame_paths: list[str],
        on_progress: Callable[[int, str], None] | None = None,
    ) -> list[str]:
        """Use Qwen 3.5 Plus to describe each frame with retry mechanism."""
        client = self._get_qwen_client()
        descriptions: list[str] = []
        total_frames = len(frame_paths)
        on_progress = on_progress or (lambda p, m: None)

        for idx, path in enumerate(frame_paths, 1):
            img_b64 = base64.b64encode(Path(path).read_bytes()).decode()

            for attempt in range(FRAME_DESC_MAX_RETRIES):
                try:
                    resp = client.chat.completions.create(
                        model="qwen3.5-plus",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                                    },
                                    {
                                        "type": "text",
                                        "text": (
                                            "请详细描述这个视频帧的画面内容，包括：\n"
                                            "1. 人物外貌特征（性别、年龄、种族、穿着、配饰、表情、动作姿态）\n"
                                            "2. 场景环境（室内/室外、具体场所、背景细节）\n"
                                            "3. 色调和光影（整体色调倾向、光源方向、明暗对比）\n"
                                            "4. 画面中的文字、标志或特殊视觉元素\n"
                                            "5. 整体氛围和情绪\n"
                                            "请用中文详细回答，不少于100字。"
                                        ),
                                    },
                                ],
                            }
                        ],
                        temperature=0.3,
                        max_tokens=800,
                        extra_body={"enable_thinking": False},
                    )
                    content = resp.choices[0].message.content or ""
                    # Strip thinking tags from Qwen3 reasoning
                    content = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', content, flags=re.DOTALL).strip()
                    descriptions.append(content)
                    logger.info(f"Frame {idx}/{total_frames} described successfully")

                    progress = int((idx / total_frames) * 100)
                    on_progress(progress, f"Analyzing frame {idx}/{total_frames}")
                    break

                except Exception as e:
                    logger.warning(f"Frame {idx} failed on attempt {attempt + 1}/{FRAME_DESC_MAX_RETRIES}: {e}")
                    if attempt < FRAME_DESC_MAX_RETRIES - 1:
                        time.sleep(FRAME_DESC_RETRY_DELAY * (attempt + 1))
                    else:
                        descriptions.append(f"[描述失败: {e}]")
                        logger.error(f"Frame {idx} failed after {FRAME_DESC_MAX_RETRIES} retries: {e}")
                        progress = int((idx / total_frames) * 100)
                        on_progress(progress, f"Frame {idx}/{total_frames} failed")

        success_count = sum(1 for d in descriptions if not d.startswith("["))
        logger.info(f"Frame description complete: {success_count}/{total_frames} successful")

        return descriptions

    # ── structural analysis ───────────────────────────────────────────────────

    def analyze_content(self, metadata: dict, frame_descriptions: list[str]) -> dict:
        """Use Qwen 3.5 Plus to produce structured analysis JSON with retry mechanism."""
        client = self._get_qwen_client()

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
            "你是一个专业的短视频分析师，擅长深入分析短视频的爆款要素、叙事结构、视觉风格和受众心理。\n\n"
            "请根据以下视频元数据和关键帧描述，输出一份详细的 JSON 格式分析报告。\n\n"
            f"【视频元数据】\n{meta_text}\n\n"
            f"【关键帧描述（共{len(frame_descriptions)}帧）】\n{frames_text}\n\n"
            "请严格按照以下结构输出 JSON（不要包含任何其他文字和标记）:\n"
            "```json\n"
            "{\n"
            '  "theme": "视频主题，如：逆袭/励志、母爱亲情、搞笑幽默、情感共鸣等",\n'
            '  "narrative_type": "叙事类型，如：线性叙事、倒叙式、反转式、三段式、对比式转折等",\n'
            '  "narrative_structure": "详细描述叙事结构，包括：开端（时间范围+内容）、发展（时间范围+内容）、高潮（时间范围+内容）、结局（时间范围+内容），每个阶段要说明对应的情感变化",\n'
            '  "emotion_curve": "情感曲线，格式如：压抑→期待→紧张→狂喜→圆满，要标注每个情感触发点",\n'
            '  "emotion_triggers": "情感触发点分析，包括：哭点是什么、燃点是什么、爽点是什么（标注核心情感）",\n'
            '  "story_summary": "用800-1200字详细描述整个视频的故事情节，按时间线逐段描述：开头场景的环境氛围、人物状态；情节发展中的关键动作和转折点；高潮部分的视觉冲击和情感释放；结局的呈现方式和整体感受",\n'
            '  "visual_style": "视觉风格分析，包括：整体色调（如灰暗vs明亮）、光影特点、画面质感",\n'
            '  "visual_contrast": "视觉对比分析，包括：场景对比、色彩对比、服饰对比、人物状态对比",\n'
            '  "visual_symbols": [{"symbol": "符号名称", "meaning": "象征意义"}],\n'
            '  "audience_profile": "受众画像分析，包括：核心受众是谁、次要受众是谁、他们的情感需求是什么",\n'
            '  "viral_elements": {\n'
            '    "topic_layer": ["话题层爆点"],\n'
            '    "emotion_layer": ["情感层爆点"],\n'
            '    "execution_layer": ["执行层亮点"]\n'
            '  },\n'
            '  "reusable_elements": {\n'
            '    "narrative_template": "可复用的叙事模板",\n'
            '    "visual_template": "可复用的视觉模板",\n'
            '    "title_formula": "标题公式/套路总结"\n'
            '  },\n'
            '  "success_factors": ["成功因素1", "成功因素2", "..."],\n'
            '  "title_formula": "标题公式总结",\n'
            '  "characters_ethnicity": "详细描述人物外貌、种族、年龄、地域特征、穿着风格，要尽可能详细"\n'
            "}\n"
            "```\n\n"
            "注意事项：\n"
            "1. story_summary 要详细具体，800字以上，不要泛泛而谈\n"
            "2. visual_symbols 必须是数组格式，每个元素是 {\"symbol\": \"名称\", \"meaning\": \"意义\"}\n"
            "3. viral_elements 要分三个层次，每层至少2个具体分析点\n"
            "4. characters_ethnicity 要详细描述所有出现的人物特征\n"
            "5. narrative_structure、visual_style、visual_contrast、emotion_triggers、audience_profile 都必须是纯文本字符串，不要用字典格式\n"
            "6. 所有字符串值必须是纯文本，不要返回 Python 字典格式\n"
            "7. 确保 JSON 格式正确，可以被直接解析"
        )

        for attempt in range(STRUCTURAL_MAX_RETRIES):
            try:
                logger.info(f"Structural analysis attempt {attempt + 1}/{STRUCTURAL_MAX_RETRIES}")
                resp = client.chat.completions.create(
                    model="qwen3.5-plus",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=8000,
                    extra_body={"enable_thinking": False},
                )
                text = resp.choices[0].message.content or ""
                # Strip thinking tags from Qwen3 reasoning
                text = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', text, flags=re.DOTALL).strip()
                result = self._parse_json_response(text)
                logger.info("Structural analysis completed successfully")
                return result

            except Exception as e:
                logger.warning(f"Structural analysis failed on attempt {attempt + 1}/{STRUCTURAL_MAX_RETRIES}: {e}")
                if attempt < STRUCTURAL_MAX_RETRIES - 1:
                    time.sleep(STRUCTURAL_RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Structural analysis failed after {STRUCTURAL_MAX_RETRIES} retries: {e}")
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
            "narrative_structure": "",
            "story_summary": "",
            "emotion_curve": "",
            "emotion_triggers": "",
            "visual_style": "",
            "visual_contrast": "",
            "viral_elements": {"topic_layer": [], "emotion_layer": [], "execution_layer": []},
            "visual_symbols": [],
            "audience_profile": "",
            "reusable_elements": {"narrative_template": "", "visual_template": "", "title_formula": ""},
            "success_factors": [],
            "title_formula": "",
            "characters_ethnicity": "",
        }

    @staticmethod
    def _generate_markdown_report(metadata: dict, descriptions: list[str], report: dict) -> str:
        """Generate a Markdown formatted report from the analysis results."""
        lines = []

        # Header
        lines.append(f"# {metadata['title']}\n")

        # Metadata section
        lines.append("## 视频信息\n")
        lines.append(f"- **平台**: {metadata.get('platform', '未知')}")
        lines.append(f"- **时长**: {metadata['duration']}秒")
        lines.append(f"- **上传者**: {metadata.get('uploader', '未知')}")
        if metadata.get('view_count'):
            lines.append(f"- **播放量**: {metadata['view_count']:,}")
        if metadata.get('like_count'):
            lines.append(f"- **点赞数**: {metadata['like_count']:,}")
        lines.append("")

        # Theme and narrative
        if report.get('theme'):
            lines.append(f"## 主题\n\n{report['theme']}\n")

        if report.get('narrative_type'):
            lines.append(f"## 叙事类型\n\n{report['narrative_type']}\n")

        # Story summary
        if report.get('story_summary'):
            lines.append(f"## 故事内容\n\n{report['story_summary']}\n")

        # Narrative structure
        if report.get('narrative_structure'):
            lines.append(f"## 叙事结构\n\n{report['narrative_structure']}\n")

        # Emotion curve
        if report.get('emotion_curve'):
            lines.append(f"## 情感曲线\n\n{report['emotion_curve']}\n")

        # Emotion triggers
        if report.get('emotion_triggers'):
            lines.append(f"## 情感触发点\n\n{report['emotion_triggers']}\n")

        # Visual style
        if report.get('visual_style'):
            lines.append(f"## 视觉风格\n\n{report['visual_style']}\n")

        # Visual contrast
        if report.get('visual_contrast'):
            lines.append(f"## 视觉对比\n\n{report['visual_contrast']}\n")

        # Visual symbols
        if report.get('visual_symbols'):
            lines.append("## 视觉符号\n")
            for symbol in report['visual_symbols']:
                if isinstance(symbol, dict):
                    lines.append(f"- **{symbol.get('symbol', '')}**: {symbol.get('meaning', '')}")
                elif isinstance(symbol, str):
                    lines.append(f"- {symbol}")
            lines.append("")

        # Viral elements
        viral = report.get('viral_elements', {})
        if viral:
            lines.append("## 爆款元素\n")

            if viral.get('topic_layer'):
                lines.append("### 话题层")
                for item in viral['topic_layer']:
                    lines.append(f"- {item}")
                lines.append("")

            if viral.get('emotion_layer'):
                lines.append("### 情感层")
                for item in viral['emotion_layer']:
                    lines.append(f"- {item}")
                lines.append("")

            if viral.get('execution_layer'):
                lines.append("### 执行层")
                for item in viral['execution_layer']:
                    lines.append(f"- {item}")
                lines.append("")

        # Audience profile
        if report.get('audience_profile'):
            lines.append(f"## 受众画像\n\n{report['audience_profile']}\n")

        # Reusable elements
        reusable = report.get('reusable_elements', {})
        if reusable:
            lines.append("## 可复用元素\n")

            if reusable.get('narrative_template'):
                lines.append(f"### 叙事模板\n\n{reusable['narrative_template']}\n")

            if reusable.get('visual_template'):
                lines.append(f"### 视觉模板\n\n{reusable['visual_template']}\n")

            if reusable.get('title_formula'):
                lines.append(f"### 标题公式\n\n{reusable['title_formula']}\n")

        # Success factors
        if report.get('success_factors'):
            lines.append("## 成功因素\n")
            for factor in report['success_factors']:
                lines.append(f"- {factor}")
            lines.append("")

        # Title formula
        if report.get('title_formula'):
            lines.append(f"## 标题公式\n\n{report['title_formula']}\n")

        # Characters ethnicity
        if report.get('characters_ethnicity'):
            lines.append(f"## 人物特征\n\n{report['characters_ethnicity']}\n")

        # Frame descriptions (optional, as appendix)
        if descriptions:
            lines.append("## 关键帧描述\n")
            for i, desc in enumerate(descriptions, 1):
                lines.append(f"### 帧 {i}\n")
                lines.append(f"{desc}\n")

        return "\n".join(lines)
