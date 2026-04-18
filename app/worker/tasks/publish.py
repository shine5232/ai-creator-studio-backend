"""Celery task for async video publishing to social platforms."""

from datetime import datetime

from app.utils.logger import logger
from app.worker.celery_app import celery_app
from app.worker.db import get_sync_session
from app.worker.tasks.base import BaseWorkflowTask, run_async


@celery_app.task(
    bind=True,
    base=BaseWorkflowTask,
    name="app.worker.tasks.publish.publish_video",
    soft_time_limit=1800,
    time_limit=2400,
)
def publish_video_task(self, record_id: int, workflow_step_id: int):
    """Publish a video to the target social platform.

    Steps:
    1. Load PublishRecord + SocialAccount from DB
    2. Resolve video file path
    3. Validate cookies
    4. Upload via platform adapter
    5. Write result back to PublishRecord
    """
    import json
    from app.models.publish import PublishRecord, SocialAccount
    from app.models.project import Project, WorkflowStep
    from app.models.asset import Asset
    from app.services.publishers.registry import publisher_registry

    with get_sync_session() as session:
        # ── Load record ──────────────────────────────────────────────────
        record: PublishRecord = session.get(PublishRecord, record_id)
        if not record:
            logger.error(f"PublishRecord {record_id} not found")
            return

        account: SocialAccount = session.get(SocialAccount, record.account_id)
        if not account:
            record.status = "failed"
            record.error_message = "SocialAccount not found"
            session.commit()
            return

        # Mark step as running
        step = session.get(WorkflowStep, workflow_step_id)
        if step:
            step.status = "running"
            step.started_at = datetime.utcnow()
            session.commit()

        # ── Resolve video path ───────────────────────────────────────────
        video_path = None
        if record.asset_id:
            asset = session.get(Asset, record.asset_id)
            if asset:
                video_path = asset.file_path
        if not video_path:
            project = session.get(Project, record.project_id)
            if project:
                video_path = project.output_video_path

        if not video_path:
            record.status = "failed"
            record.error_message = "No video file path found"
            session.commit()
            self.update_progress(workflow_step_id, 100, "Failed: no video file")
            return

    # ── Cookie validation ────────────────────────────────────────────────
    self.update_progress(workflow_step_id, 10, "Validating cookies")

    cookies = json.loads(account.auth_data) if account.auth_data else {}
    platform = account.platform

    publisher = publisher_registry.get_publisher(platform)
    if not publisher:
        with get_sync_session() as session:
            record = session.get(PublishRecord, record_id)
            record.status = "failed"
            record.error_message = f"Unsupported platform: {platform}"
            session.commit()
        return

    valid = run_async(publisher.validate_cookies(cookies))
    if not valid:
        with get_sync_session() as session:
            record = session.get(PublishRecord, record_id)
            record.status = "failed"
            record.error_message = "cookie_expired"
            session.commit()
        self.update_progress(workflow_step_id, 100, "Failed: cookies expired")
        logger.warning(f"Cookies expired for account {account.id} on {platform}")
        return

    # ── Upload ───────────────────────────────────────────────────────────
    self.update_progress(workflow_step_id, 20, "Uploading video")

    tags = json.loads(record.tags) if record.tags else []

    from app.services.publishers.base import PublishContext

    ctx = PublishContext(
        video_path=video_path,
        title=record.title,
        description=record.description,
        tags=tags,
        cookies=cookies,
    )

    result = run_async(publisher.upload_video(ctx))

    # ── Write result ─────────────────────────────────────────────────────
    with get_sync_session() as session:
        record = session.get(PublishRecord, record_id)
        if result.success:
            record.status = "published"
            record.platform_post_id = result.platform_post_id
            record.platform_url = result.platform_url
            record.published_at = datetime.utcnow()

            # Update account last_publish_at
            account = session.get(SocialAccount, record.account_id)
            if account:
                account.last_publish_at = datetime.utcnow()

            logger.info(
                f"Published to {platform}: {result.platform_url} (record {record_id})"
            )
            self.update_progress(workflow_step_id, 100, "Published successfully")
        else:
            record.status = "failed"
            record.error_message = (result.error or "Unknown error")[:2000]
            logger.error(
                f"Publish failed for record {record_id}: {result.error}"
            )
            self.update_progress(workflow_step_id, 100, f"Failed: {result.error}")

        session.commit()
