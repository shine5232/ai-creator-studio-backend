"""Base Celery task class with WorkflowStep lifecycle management."""

import asyncio
from datetime import datetime

from celery import Task

from app.utils.logger import logger
from app.worker.db import get_sync_session


class BaseWorkflowTask(Task):
    """Custom Celery Task base that tracks progress via WorkflowStep."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Mark WorkflowStep as failed on task exception."""
        workflow_step_id = kwargs.get("workflow_step_id")
        if not workflow_step_id and len(args) > 0:
            # Last positional arg convention
            workflow_step_id = args[-1] if isinstance(args[-1], int) else None
        if not workflow_step_id:
            return

        try:
            with get_sync_session() as session:
                from app.models.project import WorkflowStep

                step = session.get(WorkflowStep, workflow_step_id)
                if step:
                    step.status = "failed"
                    step.error_message = str(exc)[:2000]
                    step.completed_at = datetime.utcnow()
                    session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update WorkflowStep on failure: {db_exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Mark WorkflowStep as completed on task success."""
        workflow_step_id = kwargs.get("workflow_step_id")
        if not workflow_step_id and len(args) > 0:
            workflow_step_id = args[-1] if isinstance(args[-1], int) else None
        if not workflow_step_id:
            return

        try:
            with get_sync_session() as session:
                from app.models.project import WorkflowStep

                step = session.get(WorkflowStep, workflow_step_id)
                if step:
                    step.status = "completed"
                    step.progress = 100
                    step.completed_at = datetime.utcnow()
                    session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update WorkflowStep on success: {db_exc}")

    def update_progress(self, workflow_step_id: int, progress: int, message: str = ""):
        """Update WorkflowStep progress and Celery task state."""
        self.update_state(state="PROGRESS", meta={"progress": progress, "message": message})

        if not workflow_step_id:
            return

        try:
            with get_sync_session() as session:
                from app.models.project import WorkflowStep

                step = session.get(WorkflowStep, workflow_step_id)
                if step:
                    step.progress = progress
                    session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to update progress: {db_exc}")


def run_async(coro):
    """Bridge to run an async coroutine from synchronous Celery task.

    In normal Celery worker mode, no event loop is running so asyncio.run() works.
    In eager mode (task runs inside uvicorn's event loop), we must use the
    existing loop instead.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Eager mode: we're inside a running event loop (uvicorn)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)
