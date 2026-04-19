import base64

import httpx

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger


class DoubaoAdapter(BaseAdapter):
    provider_name = "doubao"
    supported_services = [ServiceType.TEXT_TO_IMAGE, ServiceType.IMAGE_TO_IMAGE]

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self):
        self.api_key = settings.DOUBAO_API_KEY
        self.endpoint_id = settings.DOUBAO_ENDPOINT_ID

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="Doubao API key not configured")

        url = f"{self.BASE_URL}/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        model = request.model or self.endpoint_id
        payload = {
            "model": model,
            "prompt": request.prompt,
            "n": request.params.get("n", 1),
            "size": request.params.get("size", "1024x1024"),
            "response_format": "b64_json",
            "watermark": False,
        }

        # Image-to-image
        if request.service_type == ServiceType.IMAGE_TO_IMAGE and request.image_base64:
            payload["image"] = f"data:image/png;base64,{request.image_base64}"
            payload["strength"] = request.params.get("strength", 0.7)
        elif request.service_type == ServiceType.IMAGE_TO_IMAGE and request.image_url:
            # For URLs, we need to fetch and convert to base64
            async with httpx.AsyncClient(timeout=30) as client:
                img_resp = await client.get(request.image_url)
                b64 = base64.b64encode(img_resp.content).decode()
            payload["image"] = f"data:image/png;base64,{b64}"
            payload["strength"] = request.params.get("strength", 0.7)

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            if "data" not in result or len(result["data"]) == 0:
                return AIResponse(success=False, error="No image data in response")

            image_data = result["data"][0]
            if "b64_json" in image_data:
                return AIResponse(
                    success=True,
                    data={"image_b64": image_data["b64_json"], "format": "png"},
                    cost=0.0,
                )
            elif "url" in image_data:
                return AIResponse(
                    success=True,
                    data={"image_url": image_data["url"]},
                    cost=0.0,
                )
            else:
                return AIResponse(success=False, error="Unknown response format")

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Doubao API error: {e.response.status_code} - {error_detail}")
            return AIResponse(success=False, error=f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Doubao error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str) -> AIResponse:
        # Doubao image generation is synchronous, no task polling
        return AIResponse(success=False, error="Doubao does not support async tasks")

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": self.endpoint_id,
                "name": "Doubao Seedream",
                "capabilities": ["text_to_image", "image_to_image"],
            }
        ]
