"""Celery tasks for image/video generation and video merging."""

import time
from pathlib import Path

from sqlalchemy import select

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.models.script import Shot
from app.utils.logger import logger
from app.worker.celery_app import celery_app
from app.worker.db import get_sync_session
from app.worker.tasks.base import BaseWorkflowTask, run_async


# ─── Image Generation ────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.generate_images_for_shots")
def generate_images_for_shots(
    self,
    shot_ids: list[int],
    project_id: int,
    provider: str | None,
    model: str | None,
    workflow_step_id: int,
):
    """Generate images for a list of shots using the specified AI provider."""
    total = len(shot_ids)
    adapter = registry.get_provider(provider) if provider else None

    if not adapter:
        # Try to find any provider that supports text-to-image
        providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError(f"No AI provider found for image generation (requested: {provider})")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for shot_id in shot_ids:
        try:
            with get_sync_session() as session:
                shot = session.get(Shot, shot_id)
                if not shot or shot.image_status != "pending":
                    completed += 1
                    continue

                prompt = shot.image_prompt or shot.description
                if not prompt:
                    shot.image_status = "skipped"
                    completed += 1
                    continue

                request = AIRequest(
                    prompt=prompt,
                    service_type=ServiceType.TEXT_TO_IMAGE,
                    model=model,
                )

                response = run_async(adapter.generate(request))

                if response.success and response.data:
                    # Save image data
                    image_data = response.data
                    if "url" in image_data:
                        # Download and save
                        import httpx

                        img_url = image_data["url"]
                        img_resp = httpx.get(img_url, timeout=60)
                        ext = "png"
                        filename = f"shot_{shot_id}_{int(time.time())}.{ext}"
                        filepath = upload_dir / filename
                        filepath.write_bytes(img_resp.content)
                        shot.image_path = str(filepath)
                    elif "base64" in image_data:
                        import base64

                        filename = f"shot_{shot_id}_{int(time.time())}.png"
                        filepath = upload_dir / filename
                        filepath.write_bytes(base64.b64decode(image_data["base64"]))
                        shot.image_path = str(filepath)
                    elif "local_path" in image_data:
                        shot.image_path = image_data["local_path"]

                    shot.image_status = "completed"
                    shot.image_task_id = response.task_id
                else:
                    shot.image_status = "failed"
                    error_msg = response.error or "Unknown error"
                    logger.error(f"Image generation failed for shot {shot_id}: {error_msg}")

            completed += 1
            progress = int(completed / total * 100)
            self.update_progress(workflow_step_id, progress, f"Completed {completed}/{total} images")

        except Exception as e:
            logger.error(f"Error generating image for shot {shot_id}: {e}")
            try:
                with get_sync_session() as session:
                    shot = session.get(Shot, shot_id)
                    if shot:
                        shot.image_status = "failed"
            except Exception:
                pass
            completed += 1

    logger.info(f"Image generation complete: {completed}/{total} shots for project {project_id}")


# ─── Video Generation ────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.generate_videos_for_shots")
def generate_videos_for_shots(
    self,
    shot_ids: list[int],
    project_id: int,
    provider: str | None,
    model: str | None,
    workflow_step_id: int,
):
    """Generate videos for a list of shots using the specified AI provider."""
    total = len(shot_ids)
    adapter = registry.get_provider(provider) if provider else None

    if not adapter:
        providers = registry.get_providers_for_service(ServiceType.IMAGE_TO_VIDEO)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError(f"No AI provider found for video generation (requested: {provider})")

    is_async_provider = provider in ("wanx", "seedance") if provider else False
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for shot_id in shot_ids:
        try:
            with get_sync_session() as session:
                shot = session.get(Shot, shot_id)
                if not shot or shot.video_status != "pending":
                    completed += 1
                    continue

                prompt = shot.video_prompt or shot.description
                image_path = shot.image_path
                if not prompt:
                    shot.video_status = "skipped"
                    completed += 1
                    continue

                request = AIRequest(
                    prompt=prompt,
                    service_type=ServiceType.IMAGE_TO_VIDEO,
                    model=model,
                    image_url=f"file://{image_path}" if image_path else None,
                )

                response = run_async(adapter.generate(request))

                if is_async_provider and response.task_id:
                    # Polling loop for async providers
                    shot.video_task_id = response.task_id
                    shot.video_status = "processing"
                    session.commit()

                    max_wait = 600  # seconds
                    interval = 10
                    elapsed = 0

                    while elapsed < max_wait:
                        time.sleep(interval)
                        elapsed += interval

                        poll = run_async(adapter.check_task(response.task_id))
                        if poll.success and poll.data:
                            if poll.data.get("status") == "completed":
                                self._save_video_result(shot_id, poll.data, upload_dir)
                                break
                            elif poll.data.get("status") == "failed":
                                self._mark_video_failed(shot_id, poll.data.get("error", "Async task failed"))
                                break
                        # Still processing, continue polling
                    else:
                        self._mark_video_failed(shot_id, "Timeout waiting for video generation")

                elif response.success and response.data:
                    self._save_video_result(shot_id, response.data, upload_dir)
                else:
                    self._mark_video_failed(shot_id, response.error or "Unknown error")

            completed += 1
            progress = int(completed / total * 100)
            self.update_progress(workflow_step_id, progress, f"Completed {completed}/{total} videos")

        except Exception as e:
            logger.error(f"Error generating video for shot {shot_id}: {e}")
            self._mark_video_failed(shot_id, str(e))
            completed += 1

    logger.info(f"Video generation complete: {completed}/{total} shots for project {project_id}")


def _save_video_result(shot_id: int, data: dict, upload_dir: Path):
    """Save video file from AI response to disk and update shot."""
    with get_sync_session() as session:
        shot = session.get(Shot, shot_id)
        if not shot:
            return

        if "url" in data:
            import httpx

            vid_resp = httpx.get(data["url"], timeout=120)
            filename = f"shot_{shot_id}_video_{int(time.time())}.mp4"
            filepath = upload_dir / filename
            filepath.write_bytes(vid_resp.content)
            shot.video_path = str(filepath)
        elif "local_path" in data:
            shot.video_path = data["local_path"]

        shot.video_status = "completed"


def _mark_video_failed(shot_id: int, error: str):
    """Mark a shot's video as failed."""
    try:
        with get_sync_session() as session:
            shot = session.get(Shot, shot_id)
            if shot:
                shot.video_status = "failed"
    except Exception as e:
        logger.error(f"Failed to mark shot {shot_id} video as failed: {e}")


# ─── Video Merge ─────────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.merge_project_videos")
def merge_project_videos(
    self,
    project_id: int,
    add_music: bool,
    music_path: str | None,
    workflow_step_id: int,
):
    """Merge all completed shot videos into a final project video."""
    from app.services.video_merge_service import VideoMergeService

    service = VideoMergeService()
    service.merge_project_videos(
        project_id=project_id,
        add_music=add_music,
        music_path=music_path,
        on_progress=lambda p, m: self.update_progress(workflow_step_id, p, m),
    )
