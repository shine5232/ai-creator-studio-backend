import httpx

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger

GROK_API_BASE = "https://api.apimart.ai/v1"

# Size mapping: pixel dimensions → aspect ratio string
_SIZE_TO_ASPECT = {
    "1088x1920": "9:16",
    "1920x1088": "16:9",
    "1440x1440": "1:1",
}


def _extract_image_url(images_entry: dict) -> str | None:
    """Extract image URL from an APIMart images entry.

    The 'url' field can be a string or a list of strings.
    """
    raw_url = images_entry.get("url")
    if isinstance(raw_url, list) and raw_url:
        return raw_url[0]
    if isinstance(raw_url, str):
        return raw_url
    return None


class GrokAdapter(BaseAdapter):
    provider_name = "grok"
    aliases = ["apimart"]
    supported_services = [ServiceType.TEXT_TO_IMAGE, ServiceType.IMAGE_TO_IMAGE]

    def __init__(self):
        self.api_key = getattr(settings, "GROK_API_KEY", "") or ""

    def _clean_base_url(self, base_url: str) -> str:
        """Strip endpoint path suffixes if user included them."""
        clean = base_url.rstrip('/')
        for suffix in ("/images/generations", "/images/edits"):
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
        return clean

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = request.override_api_key or self.api_key
        if not api_key:
            return AIResponse(success=False, error="Grok API key not configured")

        base_url = self._clean_base_url(request.override_base_url or GROK_API_BASE)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        model = request.model or "grok-imagine-1.0-edit-apimart"
        size = request.params.get("size", "1088x1920")
        aspect = _SIZE_TO_ASPECT.get(size, "9:16")

        # Determine endpoint: edits vs generations
        # Only models with "-edit-" in name use /images/edits;
        # other models (including those with reference images) use /images/generations + image_urls
        has_image = bool(request.image_url or request.image_base64)
        is_edit = "-edit-" in model and has_image
        endpoint = "/images/edits" if is_edit else "/images/generations"
        url = f"{base_url}{endpoint}"

        payload: dict = {
            "model": model,
            "prompt": request.prompt,
            "n": 1,
        }

        if is_edit:
            # Build image_urls from request (supports multiple character refs)
            image_urls = []
            if request.image_url:
                image_urls.append(request.image_url)
            elif request.image_base64:
                # Convert raw base64 to data URI if not already
                b64 = request.image_base64
                if b64.startswith("data:"):
                    image_urls.append(b64)
                else:
                    image_urls.append(f"data:image/png;base64,{b64}")
            # Add extra reference images from multi-character matching
            for extra_b64 in request.params.get("extra_ref_images", []):
                if extra_b64.startswith("data:"):
                    image_urls.append(extra_b64)
                else:
                    image_urls.append(f"data:image/png;base64,{extra_b64}")
            if image_urls:
                payload["image_urls"] = image_urls

        # size param (for text_to_image without edit)
        if not is_edit:
            payload["size"] = aspect

        # resolution param (some APIMart models support it, e.g. doubao-seedance-4-0)
        resolution = request.params.get("resolution")
        if resolution:
            payload["resolution"] = resolution

        # image_urls for non-edit models that support reference images
        if not is_edit and (request.image_url or request.image_base64):
            image_urls = payload.get("image_urls", [])
            if request.image_url:
                image_urls.append(request.image_url)
            elif request.image_base64:
                b64 = request.image_base64
                if b64.startswith("data:"):
                    image_urls.append(b64)
                else:
                    image_urls.append(f"data:image/png;base64,{b64}")
            for extra_b64 in request.params.get("extra_ref_images", []):
                if extra_b64.startswith("data:"):
                    image_urls.append(extra_b64)
                else:
                    image_urls.append(f"data:image/png;base64,{extra_b64}")
            if image_urls:
                payload["image_urls"] = image_urls

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()

            logger.info(f"[GrokAdapter] submit response ({endpoint}): {str(result)[:500]}")

            # Submit response format:
            # {"code": 200, "data": [{"status": "submitted", "task_id": "task_xxx"}]}
            data = result.get("data")

            # data is a list of dicts
            if isinstance(data, list) and data and isinstance(data[0], dict):
                first = data[0]
                task_id = first.get("task_id")
                if task_id:
                    return AIResponse(
                        success=True,
                        task_id=task_id,
                        data={"task_id": task_id, "model": model},
                    )

            # Fallback: data is a dict
            if isinstance(data, dict):
                task_id = data.get("task_id") or data.get("id")
                if task_id:
                    return AIResponse(
                        success=True,
                        task_id=task_id,
                        data={"task_id": task_id, "model": model},
                    )

            return AIResponse(success=False, error=f"No task_id in response: {str(result)[:300]}")

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Grok API error: {e.response.status_code} - {error_detail}")
            return AIResponse(success=False, error=f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Grok error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str, *, request: AIRequest | None = None) -> AIResponse:
        api_key = (request.override_api_key if request else None) or self.api_key
        if not api_key:
            return AIResponse(success=False, error="Grok API key not configured")

        base_url = self._clean_base_url(
            (request.override_base_url if request else None) or GROK_API_BASE
        )
        url = f"{base_url}/tasks/{task_id}?language=zh"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                result = resp.json()

            logger.info(f"[GrokAdapter] check_task response: {str(result)[:500]}")

            # Response format:
            # {"code": 200, "data": {"id": "...", "status": "completed",
            #   "result": {"images": [{"url": ["https://..."], "expires_at": ...}]}}}
            data = result.get("data", {})
            if not isinstance(data, dict):
                data = {}
            status = data.get("status", "").lower()

            if status in ("completed", "succeeded"):
                images = data.get("result", {}).get("images", [])
                if images and isinstance(images[0], dict):
                    image_url = _extract_image_url(images[0])
                    if image_url:
                        return AIResponse(
                            success=True,
                            data={"status": "completed", "image_url": image_url},
                            task_id=task_id,
                        )
                return AIResponse(
                    success=False,
                    error="Task completed but no image URL in result",
                    task_id=task_id,
                )
            elif status == "failed":
                error_msg = data.get("error", data.get("message", "Unknown error"))
                return AIResponse(
                    success=False,
                    error=f"Grok task failed: {error_msg}",
                    task_id=task_id,
                    data={"status": "failed"},
                )
            else:
                # submitted, processing, pending, queued, running
                progress = data.get("progress", 0)
                return AIResponse(
                    success=True,
                    task_id=task_id,
                    data={"status": status or "processing", "progress": progress},
                )

        except Exception as e:
            logger.error(f"Grok task check error: {e}")
            return AIResponse(success=False, error=str(e), task_id=task_id)

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "grok-imagine-1.0-apimart",
                "name": "Grok Imagine (APIMart)",
                "capabilities": ["text_to_image"],
                "params": {
                    "size": ["9:16", "16:9", "1:1"],
                },
            },
            {
                "model_id": "grok-imagine-1.0-edit-apimart",
                "name": "Grok Imagine Edit (APIMart)",
                "capabilities": ["text_to_image", "image_to_image"],
                "params": {
                    "size": ["9:16", "16:9", "1:1"],
                },
            },
            {
                "model_id": "doubao-seedance-4-0",
                "name": "Doubao Seedance 4.0 (APIMart)",
                "capabilities": ["text_to_image", "image_to_image"],
                "params": {
                    "size": ["9:16", "16:9", "1:1"],
                    "resolution": ["1K", "2K"],
                },
            },
        ]
