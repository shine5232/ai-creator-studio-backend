"""Base publisher interface for platform video publishing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PublishContext:
    video_path: str
    title: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    cookies: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@dataclass
class PublishResult:
    success: bool
    platform_post_id: str | None = None
    platform_url: str | None = None
    error: str | None = None


class BasePublisher(ABC):
    platform_name: str  # "youtube" / "douyin" / "bilibili"

    @abstractmethod
    async def upload_video(self, ctx: PublishContext) -> PublishResult:
        """Upload and publish a video to the platform."""
        ...

    @abstractmethod
    async def validate_cookies(self, cookies: dict) -> bool:
        """Verify that the provided cookies are still valid."""
        ...

    @abstractmethod
    async def check_status(self, platform_post_id: str, cookies: dict) -> dict:
        """Check the publication status of a previously uploaded video."""
        ...
