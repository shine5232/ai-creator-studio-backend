"""Generic adapter for OpenAI-compatible and APIMart-style APIs.

Supports two modes (auto-detected from response):
- Sync: POST returns image data directly
- Async: POST returns task_id, poll GET endpoint until completion

Configurable via request.params["adapter_config"]:
  - generate_path: str   — POST endpoint path (default: /images/generations)
  - poll_path: str       — GET polling path template (default: /tasks/{task_id})
  - auth_prefix: str     — Authorization header prefix (default: "Bearer ")
  - async_mode: str      — "auto" (default), "always", "never"
  - poll_interval: int   — seconds between polls (default: 5)
  - poll_timeout: int    — max seconds to wait (default: 300)
  - image_url_key: str   — JSON path to image URL in sync response (default: auto-detect)
  - task_id_key: str     — JSON key for task_id in async response (default: "id")
"""

import json

import httpx

from app.ai_gateway.base import AIRequest, AIResponse, BaseAdapter, ServiceType
from app.config import settings
from app.utils.logger import logger


def _deep_get(data: dict, path: str, default=None):
    """Get a nested value from a dict using dot-separated path.

    Examples: "data.images.0.url", "result.images.0.url", "output.video_url"
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                return default
        else:
            return default
        if current is None:
            return default
    return current


class GenericAdapter(BaseAdapter):
    provider_name = "generic"
    supported_services = [
        ServiceType.TEXT_TO_IMAGE,
        ServiceType.IMAGE_TO_IMAGE,
    ]

    def __init__(self):
        self.api_key = ""

    def _get_config(self, request: AIRequest) -> dict:
        """Extract adapter config from request params."""
        raw = request.params.get("adapter_config", {})
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = {}
        return raw or {}

    async def generate(self, request: AIRequest) -> AIResponse:
        api_key = request.override_api_key or self.api_key
        if not api_key:
            return AIResponse(success=False, error="API key not configured for generic adapter")

        base_url = request.override_base_url
        if not base_url:
            return AIResponse(success=False, error="Base URL is required for generic adapter")

        cfg = self._get_config(request)

        generate_path = cfg.get("generate_path", "/images/generations")
        # Strip endpoint suffix if user included it in base URL
        for suffix in ("/images/generations",):
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
        url = f"{base_url.rstrip('/')}{generate_path}"

        auth_prefix = cfg.get("auth_prefix", "Bearer ")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{auth_prefix}{api_key}",
        }

        model = request.model or ""
        if not model:
            return AIResponse(success=False, error="Model ID is required for generic adapter")

        # Build size param — pass through as-is
        size = request.params.get("size", "1024x1024")

        payload = {
            "model": model,
            "prompt": request.prompt,
            "size": size,
            "n": request.params.get("n", 1),
        }

        # Image-to-image support
        if request.service_type == ServiceType.IMAGE_TO_IMAGE and request.image_base64:
            payload["image"] = f"data:image/png;base64,{request.image_base64}"
            payload["strength"] = request.params.get("strength", 0.7)
        elif request.service_type == ServiceType.IMAGE_TO_IMAGE and request.image_url:
            async with httpx.AsyncClient(timeout=30) as client:
                img_resp = await client.get(request.image_url)
                import base64
                b64 = base64.b64encode(img_resp.content).decode()
            payload["image"] = f"data:image/png;base64,{b64}"
            payload["strength"] = request.params.get("strength", 0.7)

        # Allow extra body fields from adapter_config
        extra_body = cfg.get("extra_body", {})
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        async_mode = cfg.get("async_mode", "auto")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            logger.info(f"[GenericAdapter] Response keys: {list(result.keys())}")

            # Determine if async based on config or auto-detection
            task_id_key = cfg.get("task_id_key", "id")
            task_id = result.get(task_id_key) or result.get("task_id")

            is_async = False
            if async_mode == "always":
                is_async = True
            elif async_mode == "never":
                is_async = False
            else:
                # Auto-detect: if response has task_id but no image data
                is_async = bool(task_id) and not self._extract_image_url(result, cfg)

            if is_async and task_id:
                return AIResponse(
                    success=True,
                    task_id=task_id,
                    data={"task_id": task_id, "model": model},
                )

            # Synchronous — try to extract image
            image_result = self._extract_sync_result(result, cfg)
            if image_result:
                return AIResponse(success=True, data=image_result)

            return AIResponse(
                success=False,
                error=f"Cannot extract image from response. Keys: {list(result.keys())}. "
                      f"Use adapter_config.image_url_key to specify the JSON path.",
            )

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Generic adapter API error: {e.response.status_code} - {error_detail}")
            return AIResponse(success=False, error=f"HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Generic adapter error: {e}")
            return AIResponse(success=False, error=str(e))

    async def check_task(self, task_id: str, *, request: AIRequest | None = None) -> AIResponse:
        api_key = (request.override_api_key if request else None) or self.api_key
        if not api_key:
            return AIResponse(success=False, error="API key not configured")

        base_url = (request.override_base_url if request else None) or ""
        if not base_url:
            return AIResponse(success=False, error="Base URL is required for generic adapter")

        cfg = self._get_config(request) if request else {}

        poll_path_template = cfg.get("poll_path", "/tasks/{task_id}")
        # Strip endpoint suffix if user included it in base URL
        for suffix in ("/images/generations",):
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
        poll_path = poll_path_template.replace("{task_id}", task_id)
        url = f"{base_url.rstrip('/')}{poll_path}"

        auth_prefix = cfg.get("auth_prefix", "Bearer ")
        headers = {
            "Authorization": f"{auth_prefix}{api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()

            # Try common status fields
            status = (
                result.get("data", {}).get("status")
                or result.get("status")
                or result.get("output", {}).get("task_status")
                or ""
            ).lower()

            if status in ("completed", "succeeded"):
                # Extract image from result
                image_url = self._extract_image_url(result, cfg)
                if image_url:
                    return AIResponse(
                        success=True,
                        data={"status": "completed", "image_url": image_url},
                        task_id=task_id,
                    )
                # Try to extract from nested structures
                image_result = self._extract_sync_result(result, cfg)
                if image_result:
                    return AIResponse(
                        success=True,
                        data={"status": "completed", **image_result},
                        task_id=task_id,
                    )
                return AIResponse(
                    success=False,
                    error="Task completed but no image found in response",
                    task_id=task_id,
                )
            elif status == "failed":
                error_msg = (
                    _deep_get(result, "data.error")
                    or _deep_get(result, "data.message")
                    or result.get("error", {})
                    if isinstance(result.get("error"), str)
                    else str(result.get("error", "Unknown error"))
                )
                return AIResponse(
                    success=False,
                    error=f"Task failed: {error_msg}",
                    task_id=task_id,
                    data={"status": "failed"},
                )
            else:
                # processing, pending, queued, running
                return AIResponse(
                    success=True,
                    task_id=task_id,
                    data={"status": status or "processing"},
                )

        except Exception as e:
            logger.error(f"Generic adapter task check error: {e}")
            return AIResponse(success=False, error=str(e), task_id=task_id)

    def _extract_image_url(self, result: dict, cfg: dict) -> str | None:
        """Try to extract image URL from response using config or common patterns."""
        image_url_key = cfg.get("image_url_key")
        if image_url_key:
            url = _deep_get(result, image_url_key)
            if url:
                return url

        # Common patterns to try
        patterns = [
            "data.0.url",
            "data.images.0.url",
            "data.result.images.0.url",
            "output.image_url",
            "url",
            "image_url",
            "output.video_url",
        ]
        for pattern in patterns:
            url = _deep_get(result, pattern)
            if url and isinstance(url, str) and url.startswith(("http://", "https://")):
                return url

        return None

    def _extract_sync_result(self, result: dict, cfg: dict) -> dict | None:
        """Extract image data from a synchronous response."""
        # Try URL
        image_url = self._extract_image_url(result, cfg)
        if image_url:
            return {"image_url": image_url}

        # Try base64 — common patterns
        b64_patterns = [
            "data.0.b64_json",
            "data.images.0.b64_json",
            "data.base64",
            "data.image_b64",
        ]
        for pattern in b64_patterns:
            b64 = _deep_get(result, pattern)
            if b64:
                return {"image_b64": b64}

        # Try local_path
        local_path = (
            _deep_get(result, "data.local_path")
            or result.get("local_path")
        )
        if local_path:
            return {"local_path": local_path}

        return None

    def get_models(self) -> list[dict]:
        return [
            {
                "model_id": "generic",
                "name": "Generic OpenAI-Compatible",
                "capabilities": ["text_to_image", "image_to_image"],
                "params": {
                    "base_url": "Required: your API base URL",
                    "model": "Required: model identifier",
                },
            },
        ]
