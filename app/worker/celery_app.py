"""Celery application instance for AI Creator Studio async task processing."""

import platform

from celery import Celery

from app.config import settings

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "openclaw",
    broker=broker_url,
    backend=result_backend,
)

# ── Serialization & execution defaults ───────────────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    result_expires=3600,
    task_track_started=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)

# ── Pool selection ───────────────────────────────────────────────────────────
if platform.system() == "Windows":
    celery_app.conf.worker_pool = "solo"

# ── Task discovery & routing ─────────────────────────────────────────────────
# All tasks go to the default celery queue for now;
# add queue routing when multiple workers are deployed.

# Explicitly import task modules so they register with Celery
import app.worker.tasks.generation  # noqa: F401, E402
import app.worker.tasks.knowledge  # noqa: F401, E402
import app.worker.tasks.publish  # noqa: F401, E402


@celery_app.on_after_configure.connect
def setup_providers(sender, **kwargs):
    """Register AI providers in the worker process."""
    from app.ai_gateway.registry import registry
    from app.ai_gateway.providers.doubao_adapter import DoubaoAdapter
    from app.ai_gateway.providers.wanx_adapter import WanxAdapter
    from app.ai_gateway.providers.seedance_adapter import SeedanceAdapter
    from app.ai_gateway.providers.nano_banana_adapter import NanoBananaAdapter
    from app.ai_gateway.providers.glm_adapter import GLMAdapter

    registry.register(DoubaoAdapter())
    registry.register(WanxAdapter())
    registry.register(SeedanceAdapter())
    registry.register(NanoBananaAdapter())
    registry.register(GLMAdapter())

    # Register publish adapters
    from app.services.publishers.registry import publisher_registry
    from app.services.publishers.bilibili_publisher import BilibiliPublisher
    from app.services.publishers.douyin_publisher import DouyinPublisher
    from app.services.publishers.youtube_publisher import YouTubePublisher

    publisher_registry.register(BilibiliPublisher())
    publisher_registry.register(DouyinPublisher())
    publisher_registry.register(YouTubePublisher())
