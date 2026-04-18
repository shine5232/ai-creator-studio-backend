import base64
from io import BytesIO

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger


class NanoBananaAdapter(BaseAdapter):
    provider_name = "nano_banana"
    supported_services = [ServiceType.TEXT_TO_IMAGE, ServiceType.IMAGE_TO_IMAGE]

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = self.api_key
        if not api_key:
            return AIResponse(success=False, error="Gemini API key not configured")

        try:
            from google import genai
            from google.genai import types
            from PIL import Image as PILImage
        except ImportError:
            return AIResponse(success=False, error="google-genai or Pillow not installed")

        try:
            client = genai.Client(api_key=api_key)

            resolution = request.params.get("resolution", "1K")

            # Build contents
            contents = None
            if request.service_type == ServiceType.IMAGE_TO_IMAGE:
                # Load input image
                input_image = None
                if request.image_base64:
                    img_bytes = base64.b64decode(request.image_base64)
                    input_image = PILImage.open(BytesIO(img_bytes))
                elif request.image_url:
                    import httpx
                    async with httpx.AsyncClient(timeout=30) as http:
                        resp = await http.get(request.image_url)
                        input_image = PILImage.open(BytesIO(resp.content))

                if input_image:
                    contents = [input_image, request.prompt]
                else:
                    contents = request.prompt
            else:
                contents = request.prompt

            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(image_size=resolution),
                ),
            )

            # Process response
            image_b64 = None
            text_response = None
            for part in response.parts:
                if part.text is not None:
                    text_response = part.text
                elif part.inline_data is not None:
                    img_data = part.inline_data.data
                    if isinstance(img_data, str):
                        img_data = base64.b64decode(img_data)
                    image_b64 = base64.b64encode(img_data).decode()

            if not image_b64:
                return AIResponse(
                    success=False,
                    error="No image generated in response",
                    data={"text": text_response} if text_response else None,
                )

            result_data = {"image_b64": image_b64, "format": "png"}
            if text_response:
                result_data["text"] = text_response
            return AIResponse(success=True, data=result_data)

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str) -> AIResponse:
        # Gemini generation is synchronous
        return AIResponse(success=False, error="Gemini does not support async tasks")

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "gemini-3-pro-image-preview",
                "name": "Gemini 3 Pro Image (Nano Banana Pro)",
                "capabilities": ["text_to_image", "image_to_image"],
                "params": {"resolution": ["1K", "2K", "4K"]},
            }
        ]
