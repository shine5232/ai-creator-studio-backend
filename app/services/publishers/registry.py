"""Publisher registry — mirrors the ai_gateway/registry pattern."""

from app.services.publishers.base import BasePublisher


class PublisherRegistry:
    def __init__(self):
        self._publishers: dict[str, BasePublisher] = {}

    def register(self, publisher: BasePublisher):
        self._publishers[publisher.platform_name] = publisher

    def get_publisher(self, platform: str) -> BasePublisher | None:
        return self._publishers.get(platform)

    def list_platforms(self) -> list[str]:
        return list(self._publishers.keys())


publisher_registry = PublisherRegistry()
