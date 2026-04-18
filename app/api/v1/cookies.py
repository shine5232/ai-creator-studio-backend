"""Cookie management API for yt-dlp authentication."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from fastapi import Depends

router = APIRouter(prefix="/cookies", tags=["Cookies"])

COOKIES_DIR = Path("data/cookies")
ALLOWED_PLATFORMS = {"youtube", "douyin", "xiaohongshu", "kuaishou"}

PLATFORM_LABELS = {
    "youtube": "YouTube",
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "kuaishou": "快手",
}


class SaveCookieRequest(BaseModel):
    content: str


@router.get("")
async def list_cookies(
    current_user: User = Depends(get_current_user),
):
    """List cookie configuration status for all supported platforms."""
    result = []
    for platform in sorted(ALLOWED_PLATFORMS):
        cookie_file = COOKIES_DIR / f"{platform}.txt"
        result.append({
            "platform": platform,
            "label": PLATFORM_LABELS[platform],
            "configured": cookie_file.exists(),
        })
    return result


@router.get("/{platform}")
async def get_cookie(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    """Get cookie content for a specific platform (line count only, content masked)."""
    if platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    cookie_file = COOKIES_DIR / f"{platform}.txt"
    if not cookie_file.exists():
        return {"platform": platform, "configured": False}

    content = cookie_file.read_text(encoding="utf-8")
    lines = [l for l in content.splitlines() if l.strip() and not l.startswith("#")]
    return {
        "platform": platform,
        "configured": True,
        "line_count": len(lines),
        "preview": _mask_content(content),
    }


@router.post("/{platform}")
async def save_cookie(
    platform: str,
    data: SaveCookieRequest,
    current_user: User = Depends(get_current_user),
):
    """Save cookie content for a specific platform."""
    if platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Cookie content cannot be empty")

    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    cookie_file = COOKIES_DIR / f"{platform}.txt"
    cookie_file.write_text(content + "\n", encoding="utf-8")

    return {"platform": platform, "configured": True, "message": "Cookie saved"}


@router.delete("/{platform}")
async def delete_cookie(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    """Delete cookie file for a specific platform."""
    if platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    cookie_file = COOKIES_DIR / f"{platform}.txt"
    if cookie_file.exists():
        cookie_file.unlink()
        return {"platform": platform, "configured": False, "message": "Cookie deleted"}
    return {"platform": platform, "configured": False, "message": "No cookie to delete"}


def _mask_content(content: str) -> str:
    """Return masked preview: keep first column (domain), mask cookie values."""
    lines = content.splitlines()[:20]  # preview up to 20 lines
    masked = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            masked.append(line)
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            # Netscape format: domain, include_subdomains, path, secure, expires, name, value
            parts[6] = "***"
            masked.append("\t".join(parts))
        else:
            masked.append(line)
    return "\n".join(masked)
