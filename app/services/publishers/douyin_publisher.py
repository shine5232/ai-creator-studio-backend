"""Douyin (TikTok China) video publisher — OSS-based upload."""

import os

import httpx

from app.services.publishers.base import BasePublisher, PublishContext, PublishResult
from app.utils.logger import logger

DOUYIN_CREATOR_BASE = "https://creator.douyin.com"
UPLOAD_PARAMS_URL = f"{DOUYIN_CREATOR_BASE}/web/api/v1/aweme/uploadparams/"
CREATE_URL = f"{DOUYIN_CREATOR_BASE}/web/api/v1/aweme/create/"
USER_INFO_URL = f"{DOUYIN_CREATOR_BASE}/web/api/v1/user/info/"

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": f"{DOUYIN_CREATOR_BASE}/",
}


class DouyinPublisher(BasePublisher):
    platform_name = "douyin"

    # ── cookie validation ────────────────────────────────────────────────────

    async def validate_cookies(self, cookies: dict) -> bool:
        try:
            async with httpx.AsyncClient(
                cookies=cookies, headers=COMMON_HEADERS, timeout=15,
            ) as client:
                csrf = cookies.get("passport_csrf_token", "")
                headers = {**COMMON_HEADERS, "X-Csrf-Token": csrf}
                resp = await client.get(USER_INFO_URL, headers=headers)
                data = resp.json()
                return bool(data.get("data", {}).get("user"))
        except Exception as exc:
            logger.warning(f"Douyin cookie validation failed: {exc}")
            return False

    # ── status check ─────────────────────────────────────────────────────────

    async def check_status(self, platform_post_id: str, cookies: dict) -> dict:
        # 抖音暂无公开的视频状态 API
        return {"aweme_id": platform_post_id, "status": "unknown"}

    # ── upload ───────────────────────────────────────────────────────────────

    async def upload_video(self, ctx: PublishContext) -> PublishResult:
        if not os.path.isfile(ctx.video_path):
            return PublishResult(success=False, error=f"Video file not found: {ctx.video_path}")

        cookies = ctx.cookies
        csrf = cookies.get("passport_csrf_token", "")
        headers = {**COMMON_HEADERS, "X-Csrf-Token": csrf}

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    cookies=cookies, headers=headers, timeout=60,
                ) as client:
                    # Step 1: get OSS upload params
                    params_resp = await client.post(UPLOAD_PARAMS_URL)
                    params_resp.raise_for_status()
                    oss = params_resp.json().get("data", {})
                    if not oss:
                        raise RuntimeError(f"Failed to get OSS params: {params_resp.text[:500]}")

                    # Step 2: upload to OSS
                    file_size = os.path.getsize(ctx.video_path)
                    filename = os.path.basename(ctx.video_path)
                    with open(ctx.video_path, "rb") as f:
                        upload_resp = await client.post(
                            oss["host"],
                            files={"file": (filename, f, "video/mp4")},
                            data={
                                "key": oss.get("key", filename),
                                "policy": oss.get("policy", ""),
                                "OSSAccessKeyId": oss.get("OSSAccessKeyId", ""),
                                "signature": oss.get("signature", ""),
                                "callback": oss.get("callback", ""),
                            },
                            timeout=300,
                        )
                    upload_resp.raise_for_status()

                    # Step 3: publish / create aweme
                    create_resp = await client.post(
                        CREATE_URL,
                        json={
                            "title": ctx.title,
                            "desc": ctx.description or "",
                            "tags": ctx.tags or [],
                            "video_id": oss.get("key", ""),
                        },
                    )
                    create_resp.raise_for_status()
                    create_data = create_resp.json()
                    aweme_id = create_data.get("data", {}).get("aweme_id")

                    if not aweme_id:
                        raise RuntimeError(f"Douyin create returned no aweme_id: {create_data}")

                    return PublishResult(
                        success=True,
                        platform_post_id=str(aweme_id),
                        platform_url=f"https://www.douyin.com/video/{aweme_id}",
                    )
            except Exception as exc:
                logger.warning(f"Douyin upload attempt {attempt}/{max_retries} failed: {exc}")
                if attempt == max_retries:
                    return PublishResult(success=False, error=str(exc))

        # Should not reach here
        return PublishResult(success=False, error="Max retries exceeded")
