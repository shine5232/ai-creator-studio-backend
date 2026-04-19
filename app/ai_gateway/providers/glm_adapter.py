import asyncio
import re

from openai import OpenAI

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger


class GLMAdapter(BaseAdapter):
    provider_name = "glm"
    supported_services = [ServiceType.TEXT_GENERATION]

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="DashScope API key not configured")

        model = request.model or "qwen3.5-plus"
        temperature = request.params.get("temperature", 0.7)
        max_tokens = request.params.get("max_tokens", 8192)
        timeout = request.params.get("timeout", 300)

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._sync_call, api_key, model, request.prompt, temperature, max_tokens),
                timeout=timeout,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Qwen timeout after {timeout}s")
            return AIResponse(success=False, error=f"AI generation timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Qwen error: {e}")
            return AIResponse(success=False, error=str(e))

    @staticmethod
    def _sync_call(api_key: str, model: str, prompt: str, temperature: float, max_tokens: int) -> AIResponse:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        content = response.choices[0].message.content or ""
        # Strip thinking tags from Qwen3 reasoning
        content = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', content, flags=re.DOTALL).strip()
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
        return AIResponse(success=False, error="Qwen text generation is synchronous")

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "qwen3.5-plus",
                "name": "Qwen 3.5 Plus (Default)",
                "capabilities": ["text_generation"],
                "params": {"temperature": {"min": 0, "max": 1, "default": 0.7}},
            },
        ]
