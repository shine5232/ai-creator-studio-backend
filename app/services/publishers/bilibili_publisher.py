"""Bilibili video publisher — httpx-based chunked upload."""

import os

import httpx

from app.services.publishers.base import BasePublisher, PublishContext, PublishResult
from app.utils.logger import logger

BILIBILI_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
PREUPLOAD_URL = "https://member.bilibili.com/preupload"
ADD_URL = "https://member.bilibili.com/x/vu/client/add"


class BilibiliPublisher(BasePublisher):
    platform_name = "bilibili"

    # ── cookie validation ────────────────────────────────────────────────────

    async def validate_cookies(self, cookies: dict) -> bool:
        try:
            async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
                resp = await client.get(BILIBILI_NAV_URL)
                data = resp.json()
                return data.get("data", {}).get("isLogin", False)
        except Exception as exc:
            logger.warning(f"Bilibili cookie validation failed: {exc}")
            return False

    # ── status check ─────────────────────────────────────────────────────────

    async def check_status(self, platform_post_id: str, cookies: dict) -> dict:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={platform_post_id}"
        try:
            async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
                resp = await client.get(url)
                data = resp.json().get("data", {})
                return {
                    "bvid": data.get("bvid"),
                    "title": data.get("title"),
                    "stat": data.get("stat", {}),
                }
        except Exception as exc:
            logger.warning(f"Bilibili status check failed: {exc}")
            return {"error": str(exc)}

    # ── upload ───────────────────────────────────────────────────────────────

    async def upload_video(self, ctx: PublishContext) -> PublishResult:
        if not os.path.isfile(ctx.video_path):
            return PublishResult(success=False, error=f"Video file not found: {ctx.video_path}")

        cookies = ctx.cookies
        file_size = os.path.getsize(ctx.video_path)
        filename = os.path.basename(ctx.video_path)

        try:
            async with httpx.AsyncClient(cookies=cookies, timeout=60) as client:
                # Step 1: preupload
                pre = await self._preupload(client, cookies, filename, file_size)

                upos_uri = pre["upos_uri"]
                biz_id = pre["biz_id"]
                chunk_size = pre["chunk_size"]
                endpoint = pre["endpoint"]
                auth = pre["auth"]

                upload_url = f"{endpoint}/{upos_uri}"

                # Step 2: chunked upload
                chunks = (file_size + chunk_size - 1) // chunk_size
                with open(ctx.video_path, "rb") as f:
                    for i in range(chunks):
                        chunk_data = f.read(chunk_size)
                        headers = {"Authorization": auth}
                        resp = await client.put(
                            upload_url,
                            content=chunk_data,
                            headers=headers,
                            timeout=120,
                        )
                        resp.raise_for_status()
                        logger.debug(f"Bilibili chunk {i + 1}/{chunks} uploaded")

                # Step 3: submit
                bvid = await self._submit(client, cookies, upos_uri, biz_id, ctx)

                return PublishResult(
                    success=True,
                    platform_post_id=bvid,
                    platform_url=f"https://www.bilibili.com/video/{bvid}",
                )
        except Exception as exc:
            logger.error(f"Bilibili upload failed: {exc}")
            return PublishResult(success=False, error=str(exc))

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _preupload(self, client: httpx.AsyncClient, cookies: dict,
                         filename: str, file_size: int) -> dict:
        resp = await client.post(
            PREUPLOAD_URL,
            json={
                "name": filename,
                "size": file_size,
                "r": "upos",
                "profile": "ugcfx/bup",
                "ssl": 0,
                "version": "2.14.0",
                "build": 2140000,
                "upcdn": "bda2",
                "probe_version": 20221109,
            },
            cookies=cookies,
        )
        resp.raise_for_status()
        return resp.json()

    async def _submit(self, client: httpx.AsyncClient, cookies: dict,
                      upos_uri: str, biz_id: int, ctx: PublishContext) -> str:
        import json as _json

        tag_str = ",".join(ctx.tags) if ctx.tags else ""
        desc = ctx.description or ""

        resp = await client.post(
            ADD_URL,
            json={
                "copyright": 1,
                "videos": [{"filename": upos_uri.split("/")[-1].replace(".mp4", ""),
                            "title": ctx.title,
                            "desc": "",
                            "cid": biz_id}],
                "source": "",
                "tag": tag_str,
                "tid": 122,  # 默认：野生技术协会
                "cover": "",
                "title": ctx.title,
                "tag": tag_str,
                "desc_format_id": 0,
                "desc": desc,
                "dynamic": "",
                "subtitle": {"open": 0, "lan": ""},
                "csrf": cookies.get("bili_jct", ""),
            },
            cookies=cookies,
        )
        resp.raise_for_status()
        data = resp.json()
        bvid = data.get("data", {}).get("bvid")
        if not bvid:
            raise RuntimeError(f"Bilibili submit returned no bvid: {data}")
        return bvid
