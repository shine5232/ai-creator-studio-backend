from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ServiceType(str, Enum):
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_GENERATION = "text_generation"


@dataclass
class AIRequest:
    prompt: str
    service_type: ServiceType
    model: str | None = None
    image_url: str | None = None
    image_base64: str | None = None
    last_frame_url: str | None = None
    audio_url: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class AIResponse:
    success: bool
    data: dict | None = None
    task_id: str | None = None
    cost: float = 0.0
    error: str | None = None


class BaseAdapter(ABC):
    provider_name: str
    supported_services: list[ServiceType]

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        ...

    @abstractmethod
    async def check_task(self, task_id: str) -> AIResponse:
        ...

    @abstractmethod
    def get_models(self) -> list[dict]:
        ...

    def supports(self, service_type: ServiceType) -> bool:
        return service_type in self.supported_services
