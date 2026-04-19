import asyncio

from zai import ZhipuAiClient

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger


class GLMAdapter(BaseAdapter):
    provider_name = "glm"
    supported_services = [ServiceType.TEXT_GENERATION]

    def __init__(self):
        self.api_key = settings.ZHIPU_API_KEY

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="Zhipu API key not configured")

        model = request.model or "glm-4-flash"
        temperature = request.params.get("temperature", 0.7)
        max_tokens = request.params.get("max_tokens", 4096)
        timeout = request.params.get("timeout", 240)

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._sync_call, api_key, model, request.prompt, temperature, max_tokens),
                timeout=timeout,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"GLM timeout after {timeout}s")
            return AIResponse(success=False, error=f"AI generation timed out after {timeout}s")
        except Exception as e:
            logger.error(f"GLM error: {e}")
            return AIResponse(success=False, error=str(e))

    @staticmethod
    def _sync_call(api_key: str, model: str, prompt: str, temperature: float, max_tokens: int) -> AIResponse:
        client = ZhipuAiClient(api_key=api_key)
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        usage = response.usage
        return AIResponse(
            success=True,
            data={
                "text": content,
                "model": model,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            },
            cost=0.0,
        )

    async def check_task(self, task_id: str) -> AIResponse:
        # GLM text generation is synchronous
        return AIResponse(success=False, error="GLM does not support async tasks")

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "glm-4-flash",
                "name": "GLM-4 Flash (Fast)",
                "capabilities": ["text_generation"],
                "params": {"temperature": {"min": 0, "max": 1, "default": 0.7}},
            },
            {
                "model_id": "glm-4-plus",
                "name": "GLM-4 Plus (High Quality)",
                "capabilities": ["text_generation"],
                "params": {"temperature": {"min": 0, "max": 1, "default": 0.7}},
            },
        ]
