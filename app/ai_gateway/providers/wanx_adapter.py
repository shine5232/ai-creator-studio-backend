import httpx

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger

WANX_API_BASE = "https://dashscope.aliyuncs.com/api/v1"


class WanxAdapter(BaseAdapter):
    provider_name = "wanx"
    supported_services = [ServiceType.IMAGE_TO_VIDEO]

    def __init__(self):
        self.api_key = settings.WANX_API_KEY

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = request.override_api_key or self.api_key
        if not api_key:
            return AIResponse(success=False, error="Wanx API key not configured")

        if not request.image_url:
            return AIResponse(success=False, error="image_url is required for Wanx video generation")

        base_url = request.override_base_url or WANX_API_BASE
        url = f"{base_url}/services/aigc/video-generation/video-synthesis"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-DashScope-Async": "enable",
        }

        model = request.model or "wan2.6-i2v"

        input_data: dict = {"img_url": request.image_url}
        if request.prompt:
            input_data["prompt"] = request.prompt
        if request.audio_url:
            input_data["driving_audio"] = request.audio_url

        parameters = {
            "resolution": request.params.get("resolution", "720P"),
            "duration": request.params.get("duration", 3),
            "prompt_extend": request.params.get("prompt_extend", True),
            "watermark": request.params.get("watermark", False),
        }

        payload = {
            "model": model,
            "input": input_data,
            "parameters": parameters,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            # Async response contains task_id
            task_id = result.get("output", {}).get("task_id")
            if not task_id:
                # Check if it's a synchronous success (unlikely for video)
                task_status = result.get("output", {}).get("task_status", "")
                if task_status == "SUCCEEDED":
                    video_url = result.get("output", {}).get("video_url", "")
                    return AIResponse(success=True, data={"video_url": video_url})
                return AIResponse(success=False, error=f"No task_id in response: {result}")

            return AIResponse(
                success=True,
                task_id=task_id,
                data={"task_id": task_id, "model": model},
            )

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Wanx API error: {e.response.status_code} - {error_detail}")
            return AIResponse(success=False, error=f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Wanx error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str, *, request: AIRequest | None = None) -> AIResponse:
        api_key = (request.override_api_key if request else None) or self.api_key
        if not api_key:
            return AIResponse(success=False, error="Wanx API key not configured")

        base_url = (request.override_base_url if request else None) or WANX_API_BASE
        url = f"{base_url}/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()

            task_status = result.get("output", {}).get("task_status", "UNKNOWN")
            task_metrics = result.get("usage", {})

            if task_status == "SUCCEEDED":
                video_url = result.get("output", {}).get("video_url", "")
                return AIResponse(
                    success=True,
                    data={
                        "status": "succeeded",
                        "video_url": video_url,
                        "metrics": task_metrics,
                    },
                    task_id=task_id,
                )
            elif task_status == "FAILED":
                error_msg = result.get("output", {}).get("message", "Unknown error")
                error_code = result.get("output", {}).get("code", "")
                return AIResponse(
                    success=False,
                    error=f"Wanx task failed: [{error_code}] {error_msg}",
                    task_id=task_id,
                    data={"status": "failed"},
                )
            else:
                # queued, pending, running
                return AIResponse(
                    success=True,
                    task_id=task_id,
                    data={"status": task_status.lower()},
                )

        except Exception as e:
            logger.error(f"Wanx task check error: {e}")
            return AIResponse(success=False, error=str(e), task_id=task_id)

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "wan2.6-i2v-flash",
                "name": "Wanx 2.6 Flash (Fast)",
                "capabilities": ["image_to_video"],
                "params": {
                    "resolution": ["480P", "720P", "1080P"],
                    "duration": {"min": 2, "max": 30, "default": 3},
                },
            },
            {
                "model_id": "wan2.6-i2v",
                "name": "Wanx 2.6 Standard",
                "capabilities": ["image_to_video"],
                "params": {
                    "resolution": ["480P", "720P", "1080P"],
                    "duration": {"min": 2, "max": 30, "default": 3},
                },
            },
        ]
