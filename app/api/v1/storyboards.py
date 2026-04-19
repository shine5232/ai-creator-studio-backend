import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.database import get_db
from app.api.deps import get_current_user
from app.models.script import Shot, Storyboard, Script
from app.models.user import User
from app.schemas.storyboard import (
    CreateStoryboardRequest, ShotResponse, StoryboardResponse,
    UpdateShotRequest, RegenerateImageRequest, RegenerateVideoRequest,
    BatchShotRequest,
)
from app.services.generation_service import GenerationService
from app.services.storyboard_service import StoryboardService
from app.utils.logger import logger

router = APIRouter(tags=["Storyboards"])


@router.get("/scripts/{script_id}/storyboard", response_model=StoryboardResponse)
async def get_storyboard(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    storyboard = await service.get_storyboard(script_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return storyboard


@router.post("/scripts/{script_id}/storyboard", response_model=StoryboardResponse, status_code=201)
async def create_storyboard(
    script_id: int,
    data: CreateStoryboardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    try:
        return await service.create_storyboard(script_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/storyboards/{storyboard_id}", response_model=StoryboardResponse)
async def get_storyboard_detail(
    storyboard_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    storyboard = await service.get_storyboard_detail(storyboard_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return storyboard


@router.put("/shots/{shot_id}", response_model=ShotResponse)
async def update_shot(
    shot_id: int,
    data: UpdateShotRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoryboardService(db)
    try:
        return await service.update_shot(shot_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/shots/{shot_id}/regenerate-image")
async def regenerate_image(
    shot_id: int,
    data: RegenerateImageRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    # Resolve project_id and verify ownership
    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    # Update prompt if provided, then reset status
    if data and data.image_prompt:
        shot.image_prompt = data.image_prompt
    shot.image_status = "pending"
    await db.commit()

    service = GenerationService(db)
    return await service.generate_images_batch(
        project_id,
        provider=data.provider if data else None,
        model=data.model if data else None,
        shot_ids=[shot_id],
    )


@router.post("/shots/{shot_id}/regenerate-video")
async def regenerate_video(
    shot_id: int,
    data: RegenerateVideoRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    if data and data.video_prompt:
        shot.video_prompt = data.video_prompt
    if data and data.duration:
        shot.video_duration = data.duration
    shot.video_status = "pending"
    await db.commit()

    service = GenerationService(db)
    return await service.generate_videos_batch(
        project_id,
        provider=data.provider if data else None,
        model=data.model if data else None,
        shot_ids=[shot_id],
    )


async def _get_shot_project_id(db: AsyncSession, shot: Shot) -> int:
    """Resolve project_id from a Shot via Storyboard→Script chain."""
    result = await db.execute(
        select(Script.project_id)
        .join(Storyboard, Storyboard.script_id == Script.id)
        .where(Storyboard.id == shot.storyboard_id)
    )
    return result.scalar_one()


async def _verify_project_owner(db: AsyncSession, project_id: int, user_id: int) -> bool:
    from app.models.project import Project
    result = await db.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


@router.post("/storyboards/{storyboard_id}/generate-prompts")
async def generate_prompts_for_storyboard(
    storyboard_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为分镜板中所有缺少 image_prompt 的镜头批量生成 Seedream 文生图提示词。"""
    storyboard = await db.get(Storyboard, storyboard_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    # 获取 project_id 并验证权限
    script_result = await db.execute(select(Script.project_id).where(Script.id == storyboard.script_id))
    project_id = script_result.scalar_one_or_none()
    if not project_id or not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Storyboard not found")

    # 筛选缺少 image_prompt 的镜头
    shot_result = await db.execute(
        select(Shot.id)
        .where(Shot.storyboard_id == storyboard_id)
        .where((Shot.image_prompt == None) | (Shot.image_prompt == ""))  # noqa: E711
        .order_by(Shot.shot_number)
    )
    shot_ids = [row[0] for row in shot_result.all()]

    if not shot_ids:
        return {"task_id": None, "message": "所有镜头已有提示词"}

    service = GenerationService(db)
    return await service.generate_image_prompts(shot_ids, project_id)


@router.post("/shots/{shot_id}/generate-prompt")
async def generate_shot_prompt(
    shot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """同步为单个镜头生成文生图提示词。"""
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    # 获取 script
    storyboard = await db.get(Storyboard, shot.storyboard_id)
    script = await db.get(Script, storyboard.script_id) if storyboard else None
    script_title = script.title if script else "未知脚本"

    # 从 Character 表加载人物设定
    from app.models.character import Character as CharModel
    char_result = await db.execute(
        select(CharModel).where(CharModel.project_id == project_id)
    )
    characters = char_result.scalars().all()
    char_text = ""
    if characters:
        lines = ["以下是脚本中的人物设定：\n"]
        for c in characters:
            parts = [f"- {c.name}："]
            if c.age:
                parts.append(f"{c.age}岁，")
            if c.gender:
                parts.append(f"{c.gender}，")
            if c.nationality:
                parts.append(f"{c.nationality}，")
            if c.skin_tone:
                parts.append(f"肤色{c.skin_tone}，")
            if c.appearance:
                parts.append(c.appearance)
            lines.append("".join(parts))
            if c.ethnic_features:
                lines.append(f"  特殊标记：{c.ethnic_features}")
            if c.clothing:
                lines.append(f"  穿着变化：{c.clothing}")
        char_text = "\n".join(lines)

    # fallback 到 JSON 解析
    if not char_text and script and "---STRUCTURED_DATA---" in script.content:
        from app.worker.tasks.generation import _build_character_profiles_text
        char_text = _build_character_profiles_text(script.content)

    # 提取视觉风格
    visual_style = ""
    if script and "---STRUCTURED_DATA---" in script.content:
        try:
            parts = script.content.split("---STRUCTURED_DATA---", 1)
            structured = json.loads(parts[1].strip())
            vd = structured.get("visual_design", {})
            vs_parts = []
            if vd.get("color_progression"):
                vs_parts.append(f"色调变化：{vd['color_progression']}")
            for s in vd.get("visual_symbols", []):
                vs_parts.append(f"视觉符号：{s.get('symbol', '')}({s.get('meaning', '')})")
            visual_style = "\n".join(vs_parts)
        except json.JSONDecodeError:
            pass

    # 构建 AI 请求
    from app.worker.tasks.generation import _build_prompt_for_shot
    ai_prompt = _build_prompt_for_shot(
        shot, char_text, script_title, shot.tone, shot.mood, visual_style
    )

    providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
    if not providers:
        raise HTTPException(status_code=500, detail="No text generation provider available")

    response = await providers[0].generate(AIRequest(
        prompt=ai_prompt,
        service_type=ServiceType.TEXT_GENERATION,
        params={"temperature": 0.7, "max_tokens": 1024},
    ))

    if not response.success or not response.data:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {response.error}")

    text = response.data.get("text", "").strip()
    from app.worker.tasks.generation import _parse_prompts
    image_prompt, video_prompt = _parse_prompts(text)

    if image_prompt:
        shot.image_prompt = image_prompt
    if video_prompt:
        shot.video_prompt = video_prompt
    await db.commit()

    logger.info(f"Sync generated prompts for shot {shot_id}: image={len(image_prompt)}, video={len(video_prompt)}")
    return {"shot_id": shot_id, "image_prompt": image_prompt, "video_prompt": video_prompt}


@router.post("/shots/{shot_id}/generate-image")
async def generate_shot_image(
    shot_id: int,
    data: RegenerateImageRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """同步为单个镜头生成图片。"""
    result = await db.execute(select(Shot).where(Shot.id == shot_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    project_id = await _get_shot_project_id(db, shot)
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Shot not found")

    prompt = shot.image_prompt or shot.description
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt available for this shot")

    aspect_ratio = getattr(data, "aspect_ratio", None) or "9:16" if data else "9:16"
    size_map = {"9:16": "1088x1920", "16:9": "1920x1088", "1:1": "1440x1440"}
    size = size_map.get(aspect_ratio, "1088x1920")

    providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
    if not providers:
        raise HTTPException(status_code=500, detail="No image generation provider available")

    response = await providers[0].generate(AIRequest(
        prompt=prompt,
        service_type=ServiceType.TEXT_TO_IMAGE,
        params={"size": size},
    ))

    if not response.success:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {response.error}")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    if response.data:
        if "url" in response.data or "image_url" in response.data:
            import httpx
            img_url = response.data.get("url") or response.data.get("image_url")
            img_resp = httpx.get(img_url, timeout=60)
            filename = f"shot_{shot_id}_{int(time.time())}.png"
            filepath = upload_dir / filename
            filepath.write_bytes(img_resp.content)
            shot.image_path = str(filepath)
        elif "base64" in response.data or "image_b64" in response.data:
            import base64
            b64_data = response.data.get("base64") or response.data.get("image_b64")
            filename = f"shot_{shot_id}_{int(time.time())}.png"
            filepath = upload_dir / filename
            filepath.write_bytes(base64.b64decode(b64_data))
            shot.image_path = str(filepath)
        elif "local_path" in response.data:
            shot.image_path = response.data["local_path"]

        shot.image_status = "completed"
        await db.commit()

    logger.info(f"Sync generated image for shot {shot_id}")
    return {"shot_id": shot_id, "image_path": shot.image_path, "image_status": shot.image_status}


@router.post("/projects/{project_id}/batch/character-images")
async def batch_generate_character_images(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量生成该项目所有人物的参考图。"""
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    service = GenerationService(db)
    return await service.batch_generate_character_images(project_id)


@router.post("/projects/{project_id}/batch/shot-images")
async def batch_generate_shot_images(
    project_id: int,
    data: BatchShotRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量生成该项目指定或所有待处理分镜的图片。"""
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    if data and data.shot_ids:
        shot_ids = data.shot_ids
        # 重置选中 shots 的状态为 pending，确保任务会处理它们
        await db.execute(
            Shot.__table__.update()
            .where(Shot.id.in_(shot_ids))
            .values(image_status="pending")
        )
        await db.commit()
    else:
        shot_result = await db.execute(
            select(Shot.id)
            .join(Storyboard, Shot.storyboard_id == Storyboard.id)
            .join(Script, Storyboard.script_id == Script.id)
            .where(Script.project_id == project_id)
            .where(Shot.image_status == "pending")
            .order_by(Shot.shot_number)
        )
        shot_ids = [row[0] for row in shot_result.all()]

    if not shot_ids:
        return {"task_id": None, "message": "没有待生成的分镜图片"}

    service = GenerationService(db)
    return await service.generate_images_batch(
        project_id,
        shot_ids=shot_ids,
    )


@router.post("/projects/{project_id}/batch/shot-prompts")
async def batch_generate_shot_prompts(
    project_id: int,
    data: BatchShotRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量为该项目指定或所有分镜生成文生图提示词。"""
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    if data and data.shot_ids:
        shot_ids = data.shot_ids
    else:
        shot_result = await db.execute(
            select(Shot.id)
            .join(Storyboard, Shot.storyboard_id == Storyboard.id)
            .join(Script, Storyboard.script_id == Script.id)
            .where(Script.project_id == project_id)
            .order_by(Shot.shot_number)
        )
        shot_ids = [row[0] for row in shot_result.all()]

    if not shot_ids:
        return {"task_id": None, "message": "没有需要生成提示词的分镜"}

    service = GenerationService(db)
    return await service.generate_image_prompts(shot_ids, project_id)


@router.post("/projects/{project_id}/batch/shot-videos")
async def batch_generate_shot_videos(
    project_id: int,
    data: BatchShotRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量生成该项目指定分镜的视频。"""
    if not await _verify_project_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")

    if data and data.shot_ids:
        shot_ids = data.shot_ids
        # 重置选中 shots 的状态为 pending
        await db.execute(
            Shot.__table__.update()
            .where(Shot.id.in_(shot_ids))
            .values(video_status="pending")
        )
        await db.commit()
    else:
        shot_result = await db.execute(
            select(Shot.id)
            .join(Storyboard, Shot.storyboard_id == Storyboard.id)
            .join(Script, Storyboard.script_id == Script.id)
            .where(Script.project_id == project_id)
            .where(Shot.video_status == "pending")
            .order_by(Shot.shot_number)
        )
        shot_ids = [row[0] for row in shot_result.all()]

    if not shot_ids:
        return {"task_id": None, "message": "没有待生成的分镜视频"}

    service = GenerationService(db)
    return await service.generate_videos_batch(
        project_id,
        shot_ids=shot_ids,
    )
