import httpx

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger

SEEDANCE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations"


class SeedanceAdapter(BaseAdapter):
    provider_name = "seedance"
    supported_services = [ServiceType.IMAGE_TO_VIDEO]

    def __init__(self):
        self.api_key = settings.SEEDANCE_API_KEY

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="Seedance API key not configured")

        if not request.image_url:
            return AIResponse(success=False, error="image_url (first frame) is required for Seedance")

        url = f"{SEEDANCE_BASE_URL}/tasks"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        model = request.model or "doubao-seedance-1-5-pro-251215"

        # Build text prompt with CLI-style flags
        prompt_text = request.prompt
        params = request.params
        if params.get("duration"):
            prompt_text += f" --duration {params['duration']}"
        if "camerafixed" in params:
            prompt_text += f" --camerafixed {str(params['camerafixed']).lower()}"
        if "watermark" in params:
            prompt_text += f" --watermark {str(params['watermark']).lower()}"

        content = [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": request.image_url}},
        ]

        # Optional last frame
        if request.last_frame_url:
            content.append({"type": "image_url", "image_url": {"url": request.last_frame_url}})

        payload = {
            "model": model,
            "content": content,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            task_id = result.get("id")
            if not task_id:
                return AIResponse(success=False, error=f"No task id in response: {result}")

            return AIResponse(
                success=True,
                task_id=task_id,
                data={"task_id": task_id, "model": model},
            )

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Seedance API error: {e.response.status_code} - {error_detail}")
            return AIResponse(success=False, error=f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Seedance error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="Seedance API key not configured")

        url = f"{SEEDANCE_BASE_URL}/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()

            status = result.get("status", "unknown").lower()

            if status == "succeeded":
                video_url = None
                audio_url = None
                # Try multiple response paths
                res = result.get("result", {})
                if res:
                    video_url = res.get("video_url")
                    audio_url = res.get("audio_url")
                if not video_url:
                    video_url = result.get("video_url") or result.get("output", {}).get("video_url")

                data = {"status": "succeeded"}
                if video_url:
                    data["video_url"] = video_url
                if audio_url:
                    data["audio_url"] = audio_url
                return AIResponse(success=True, task_id=task_id, data=data)

            elif status == "failed":
                error_msg = result.get("error", {}) or result.get("message", "Unknown error")
                return AIResponse(
                    success=False,
                    error=f"Seedance task failed: {error_msg}",
                    task_id=task_id,
                    data={"status": "failed"},
                )
            else:
                # queued, pending, running, processing
                return AIResponse(
                    success=True,
                    task_id=task_id,
                    data={"status": status},
                )

        except Exception as e:
            logger.error(f"Seedance task check error: {e}")
            return AIResponse(success=False, error=str(e), task_id=task_id)

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "doubao-seedance-1-5-pro-251215",
                "name": "Seedance 1.5 Pro",
                "capabilities": ["image_to_video"],
                "params": {
                    "duration": {"min": 2, "max": 10, "default": 5},
                    "first_last_frame": True,
                },
            }
        ]
