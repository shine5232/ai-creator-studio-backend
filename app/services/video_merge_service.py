"""FFmpeg-based video merge service.

Runs synchronously inside Celery worker processes.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.models.script import Script, Shot, Storyboard
from app.utils.logger import logger
from app.worker.db import get_sync_session


class VideoMergeService:
    """Handles video normalisation, concatenation, and background-music mixing."""

    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")
        if not self.ffmpeg:
            raise RuntimeError("ffmpeg not found on PATH – please install ffmpeg")
        if not self.ffprobe:
            raise RuntimeError("ffprobe not found on PATH – please install ffmpeg")

    # ── low-level helpers ─────────────────────────────────────────────────

    def probe_duration(self, video_path: str) -> float:
        """Return video duration in seconds via ffprobe."""
        cmd = [
            self.ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])

    def normalize_video(self, input_path: str, output_path: str) -> None:
        """Re-encode a clip to uniform resolution / fps / codec."""
        w = settings.VIDEO_DEFAULT_WIDTH
        h = settings.VIDEO_DEFAULT_HEIGHT
        fps = settings.VIDEO_DEFAULT_FPS

        cmd = [
            self.ffmpeg, "-y",
            "-i", str(input_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(fps),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)

    def concat_videos(self, input_paths: list[str], output_path: str) -> None:
        """Concatenate pre-normalised clips via ffmpeg concat demuxer (-c copy)."""
        filelist = Path(output_path).parent / "filelist.txt"
        try:
            with open(filelist, "w", encoding="utf-8") as f:
                for p in input_paths:
                    # escape single quotes for concat demuxer
                    escaped = str(p).replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(filelist),
                "-c", "copy",
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
        finally:
            filelist.unlink(missing_ok=True)

    def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.3,
    ) -> None:
        """Mix background music into the video (looped, volume-adjusted, trimmed)."""
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(video_path),
            "-stream_loop", "-1",
            "-i", str(music_path),
            "-filter_complex", f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)

    # ── high-level orchestration ──────────────────────────────────────────

    def merge_project_videos(
        self,
        project_id: int,
        add_music: bool,
        music_path: str | None,
        on_progress=None,
    ) -> str:
        """Full merge pipeline: query → probe → normalise → concat → mix.

        Returns the final output video path.

        Args:
            project_id: Project to merge.
            add_music: Whether to mix in background music.
            music_path: Path to the music file (required when add_music is True).
            on_progress: Callback ``(progress_pct, message)`` for progress updates.
        """
        if on_progress is None:
            on_progress = lambda p, m: None

        # 5% — query shots ------------------------------------------------
        on_progress(5, "Querying project shots…")
        shots = self._query_project_shots(project_id)
        if not shots:
            raise ValueError(f"No completed shot videos found for project {project_id}")

        video_paths = [s.video_path for s in shots if s.video_path]
        if not video_paths:
            raise ValueError(f"No video files found for project {project_id}")

        # 10% — probe durations -------------------------------------------
        on_progress(10, "Probing video durations…")
        durations: list[float] = []
        valid_paths: list[str] = []
        for vp in video_paths:
            if not Path(vp).exists():
                logger.warning(f"Video file not found, skipping: {vp}")
                continue
            try:
                dur = self.probe_duration(vp)
                durations.append(dur)
                valid_paths.append(vp)
            except Exception as exc:
                logger.warning(f"Probe failed for {vp}: {exc}")
        if not valid_paths:
            raise ValueError("Zero valid video clips after probing")

        # temp directory for intermediate files
        temp_dir = Path("data/uploads/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=str(temp_dir)) as tmp:
            tmp = Path(tmp)

            # 20-50% — normalise ------------------------------------------
            normalised: list[str] = []
            total = len(valid_paths)
            for i, vp in enumerate(valid_paths):
                out = str(tmp / f"norm_{i:04d}.mp4")
                self.normalize_video(vp, out)
                normalised.append(out)
                pct = 20 + int((i + 1) / total * 30)
                on_progress(pct, f"Normalised {i + 1}/{total} clips")

            # 50-70% — concat ---------------------------------------------
            concat_out = str(tmp / "concat.mp4")
            on_progress(50, "Concatenating clips…")
            self.concat_videos(normalised, concat_out)
            on_progress(70, "Concatenation complete")

            # 75-95% — background music -----------------------------------
            final_name = f"project_{project_id}_final_{_ts()}.mp4"
            output_dir = Path("data/uploads")
            final_path = str(output_dir / final_name)

            if add_music and music_path and Path(music_path).exists():
                on_progress(75, "Adding background music…")
                self.add_background_music(concat_out, music_path, final_path)
                on_progress(95, "Background music mixed")
            else:
                # just copy the concat result
                shutil.copy2(concat_out, final_path)
                on_progress(90, "Saving final video")

        # 100% — persist result to DB ------------------------------------
        total_duration = sum(durations)
        with get_sync_session() as session:
            from app.models.project import Project

            project = session.get(Project, project_id)
            if project:
                project.output_video_path = final_path
                project.output_duration = int(total_duration)
                project.status = "completed"
                session.commit()

        on_progress(100, f"Merge complete — {total_duration:.1f}s")
        logger.info(
            f"Merge complete for project {project_id}: {final_path} ({total_duration:.1f}s)"
        )
        return final_path

    # ── internal helpers ──────────────────────────────────────────────────

    def _query_project_shots(self, project_id: int) -> list[Shot]:
        """Query shots for a project via proper JOIN chain: Shot→Storyboard→Script→Project."""
        with get_sync_session() as session:
            stmt = (
                select(Shot)
                .join(Storyboard, Shot.storyboard_id == Storyboard.id)
                .join(Script, Storyboard.script_id == Script.id)
                .where(Script.project_id == project_id)
                .where(Shot.video_status == "completed")
                .order_by(Shot.shot_number)
            )
            result = session.execute(stmt)
            # expire_on_commit=False, but we need attrs after session close
            shots = result.scalars().all()
            # force-load attributes before session closes
            for s in shots:
                _ = s.video_path, s.shot_number
            return shots


def _ts() -> str:
    """Compact timestamp for filenames."""
    import time
    return str(int(time.time()))
