"""Celery tasks for image/video generation and video merging."""

import json
import time
from pathlib import Path

from sqlalchemy import select

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.models.character import Character
from app.models.script import Script, Shot, Storyboard
from app.utils.logger import logger
from app.worker.celery_app import celery_app
from app.worker.db import get_sync_session
from app.worker.tasks.base import BaseWorkflowTask, run_async


# ─── Image Prompt Generation ────────────────────────────────────────────────


def _build_character_profiles_text(script_content: str, project_id: int | None = None, session=None) -> str:
    """构建人物设定文本。优先从 Character 表查询，fallback 到脚本 JSON 解析。"""
    # 优先从 DB 查询
    if project_id and session:
        try:
            result = session.execute(
                select(Character).where(Character.project_id == project_id)
            )
            characters = result.scalars().all()
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
                        parts.append(f"{c.appearance}")
                    lines.append("".join(parts))
                    if c.ethnic_features:
                        lines.append(f"  特殊标记：{c.ethnic_features}")
                    if c.clothing:
                        lines.append(f"  穿着变化：{c.clothing}")
                    # 输出 periods 信息
                    for period in sorted(c.periods, key=lambda p: p.sort_order):
                        period_info = f"  【{period.period_name}】"
                        if period.clothing_delta:
                            period_info += f" 穿着：{period.clothing_delta}"
                        if period_info.strip() != f"  【{period.period_name}】":
                            lines.append(period_info)
                text = "\n".join(lines)
                if text.strip() != "以下是脚本中的人物设定：":
                    return text
        except Exception as e:
            logger.warning(f"Failed to load characters from DB: {e}")

    # Fallback：从脚本 content 中解析 JSON
    marker = "---STRUCTURED_DATA---"
    if marker not in script_content:
        return ""
    parts = script_content.split(marker, 1)
    try:
        structured = json.loads(parts[1].strip())
    except json.JSONDecodeError:
        return ""

    profiles = structured.get("character_profiles", [])
    if not profiles:
        return ""

    lines = ["以下是脚本中的人物设定：\n"]
    for p in profiles:
        clothing = ""
        if p.get("clothing_phases"):
            clothing = "；".join(
                f"{cp.get('phase', '')}: {cp.get('description', '')}"
                for cp in p["clothing_phases"]
            )
        lines.append(
            f"- {p.get('role_name', '角色')}：{p.get('age', '')}岁，"
            f"{p.get('gender', '')}，{p.get('race_ethnicity', '')}，"
            f"肤色{p.get('skin_color', '')}，眼{p.get('eyes', '')}，"
            f"发型{p.get('hair', '')}，{p.get('facial_features', '')}，"
            f"体型{p.get('body_type', '')}，特殊标记{p.get('special_marks', '')}"
        )
        if clothing:
            lines.append(f"  穿着变化：{clothing}")
    return "\n".join(lines)


def _build_prompt_for_shot(
    shot: Shot,
    character_profiles_text: str,
    script_title: str,
    tone: str | None,
    mood: str | None,
    visual_style: str,
) -> str:
    """构建用于同时生成文生图提示词和图生视频提示词的 AI 请求。"""
    return (
        "你是一个专业的AI提示词工程师。请根据以下分镜信息，同时生成两条提示词：\n"
        "1. 文生图提示词（用于 Seedream/豆包 模型生成静态图片）\n"
        "2. 图生视频提示词（用于万相/Seedance 等图生视频模型，基于已生成的图片生成动态视频）\n\n"
        "## 输出格式（严格遵守）\n"
        "【文生图提示词】\n"
        "（文生图提示词内容）\n"
        "【图生视频提示词】\n"
        "（图生视频提示词内容）\n\n"
        "## 文生图提示词要求\n"
        "1. 先写景别（特写/中景/全景/远景镜头）\n"
        "2. 再写画面主体：包含人物外貌细节（年龄、种族、肤色、发型、眼睛、体型、特殊标记）\n"
        "3. 写人物动作、表情、情绪\n"
        "4. 写环境描写（具体地点、光线、细节）\n"
        "5. 写美学短词：色调、光影、构图、氛围\n"
        "6. 结尾固定：电影感，真实照片风格，8K高清，竖屏9:16\n"
        "7. 中文为主，专业摄影术语可用英文\n\n"
        "## 图生视频提示词要求\n"
        "1. 描述画面中应该发生的动态变化和运动（如人物转头、微风吹动头发、光线变化等）\n"
        "2. 描述镜头运动（如缓慢推进、微微摇晃、固定镜头等）\n"
        "3. 简洁精准，只描述视频中的动态元素，不要重复静态描述\n"
        "4. 中文为主，英文不超过50个词\n"
        "5. 控制在1-3句话以内，图生视频提示词不宜过长\n\n"
        "## 关键规则\n"
        "- 提示词中必须嵌入完整的人物外貌特征，确保与设定一致\n"
        "- 根据分镜的幕(act)判断当前穿着时期\n"
        "- 只按指定格式返回，不要任何额外解释\n\n"
        f"## 脚本标题：{script_title}\n\n"
        f"## 人物设定\n{character_profiles_text}\n\n"
        f"## 当前镜头信息\n"
        f"- 幕名：{shot.act_name or '未知'}\n"
        f"- 景别：{shot.shot_type or '未指定'}\n"
        f"- 镜头描述：{shot.description}\n"
        f"- 色调：{tone or '未指定'}\n"
        f"- 氛围：{mood or '未指定'}\n\n"
        f"## 视觉风格参考\n{visual_style}\n\n"
        "请生成提示词："
    )


def _parse_prompts(text: str) -> tuple[str, str]:
    """从 AI 返回文本中解析文生图和图生视频提示词。"""
    # 去除 markdown 代码块
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl >= 0:
            text = text[first_nl + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

    image_prompt = ""
    video_prompt = ""

    # 尝试按标记拆分
    img_marker = "【文生图提示词】"
    vid_marker = "【图生视频提示词】"

    if img_marker in text and vid_marker in text:
        img_start = text.index(img_marker) + len(img_marker)
        vid_start = text.index(vid_marker)
        image_prompt = text[img_start:vid_start].strip()
        video_prompt = text[vid_start + len(vid_marker):].strip()
    elif img_marker in text:
        image_prompt = text[text.index(img_marker) + len(img_marker):].strip()
    elif vid_marker in text:
        video_prompt = text[text.index(vid_marker) + len(vid_marker):].strip()
    else:
        # 没有标记分隔，整段作为 image_prompt
        image_prompt = text

    return image_prompt, video_prompt


@celery_app.task(
    bind=True, base=BaseWorkflowTask,
    name="app.worker.tasks.generation.generate_image_prompts_for_shots",
    soft_time_limit=600, time_limit=900,
)
def generate_image_prompts_for_shots(
    self,
    shot_ids: list[int],
    workflow_step_id: int,
):
    """为每个分镜调用 AI 生成 Seedream 文生图提示词，保存到 shot.image_prompt。"""
    total = len(shot_ids)
    providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
    if not providers:
        raise ValueError("No text generation provider available")

    adapter = providers[0]
    completed = 0

    # 批量加载所需数据
    with get_sync_session() as session:
        shots = [session.get(Shot, sid) for sid in shot_ids]
        shots = [s for s in shots if s]

        if not shots:
            return

        # 获取 script
        storyboard = session.get(Storyboard, shots[0].storyboard_id)
        if not storyboard:
            return
        script = session.get(Script, storyboard.script_id)
        script_title = script.title if script else "未知脚本"

        # 获取 project_id（通过 script 关联）
        project_id = script.project_id if script else None

        # 提取人物设定（优先从 Character 表）
        character_profiles_text = (
            _build_character_profiles_text(
                script.content, project_id=project_id, session=session
            ) if script else ""
        )

        # 提取视觉风格
        visual_style = ""
        marker = "---STRUCTURED_DATA---"
        if script and marker in script.content:
            try:
                parts = script.content.split(marker, 1)
                structured = json.loads(parts[1].strip())
                vd = structured.get("visual_design", {})
                parts_list = []
                if vd.get("color_progression"):
                    parts_list.append(f"色调变化：{vd['color_progression']}")
                for s in vd.get("visual_symbols", []):
                    parts_list.append(f"视觉符号：{s.get('symbol', '')}({s.get('meaning', '')})")
                visual_style = "\n".join(parts_list)
            except json.JSONDecodeError:
                pass

    for shot in shots:
        try:
            prompt = _build_prompt_for_shot(
                shot, character_profiles_text, script_title,
                shot.tone, shot.mood, visual_style,
            )
            request = AIRequest(
                prompt=prompt,
                service_type=ServiceType.TEXT_GENERATION,
                params={"temperature": 0.7, "max_tokens": 1024},
            )
            response = run_async(adapter.generate(request))

            if response.success and response.data:
                text = response.data.get("text", "").strip()
                image_prompt, video_prompt = _parse_prompts(text)

                with get_sync_session() as session:
                    db_shot = session.get(Shot, shot.id)
                    if db_shot:
                        if image_prompt:
                            db_shot.image_prompt = image_prompt
                        if video_prompt:
                            db_shot.video_prompt = video_prompt
                        session.commit()

                logger.info(f"Generated prompts for shot {shot.id}: image={len(image_prompt)}, video={len(video_prompt)}")
            else:
                logger.warning(f"AI prompt generation failed for shot {shot.id}: {response.error}")

        except Exception as e:
            logger.error(f"Error generating prompt for shot {shot.id}: {e}")

        completed += 1
        progress = int(completed / total * 100)
        self.update_progress(workflow_step_id, progress, f"已完成 {completed}/{total} 个提示词")

    logger.info(f"Image prompt generation complete: {completed}/{total} shots")


# ─── Character Image Generation ──────────────────────────────────────────────


def _build_char_prompt(character, aspect_ratio: str = "9:16") -> str:
    """根据人物属性拼接文生图提示词（同步版本，复用 CharacterService 逻辑）。"""
    cn_parts = [f"{character.name}的人物肖像"]
    if character.gender:
        cn_parts.append(character.gender)
    if character.age:
        cn_parts.append(f"{character.age}岁")
    if character.nationality:
        cn_parts.append(character.nationality)
    if character.skin_tone:
        cn_parts.append(character.skin_tone)
    if character.appearance:
        cn_parts.append(character.appearance)
    if character.ethnic_features:
        cn_parts.append(character.ethnic_features)
    if character.clothing:
        cn_parts.append(f"穿着{character.clothing}")
    prompt_cn = "，".join(cn_parts)

    if aspect_ratio == "9:16":
        prompt_cn += "，竖屏构图，全身或半身肖像，高质量人物肖像，面部细节丰富，电影级光影"
    elif aspect_ratio == "16:9":
        prompt_cn += "，横屏构图，全身或环境肖像，高质量人物肖像，面部细节丰富，电影级光影"
    else:
        prompt_cn += "，高质量人物肖像，面部细节丰富，电影级光影"
    return prompt_cn


@celery_app.task(
    bind=True, base=BaseWorkflowTask,
    name="app.worker.tasks.generation.generate_character_images",
    soft_time_limit=600, time_limit=900,
)
def generate_character_images(
    self,
    character_ids: list[int],
    project_id: int,
    aspect_ratio: str = "9:16",
    workflow_step_id: int = 0,
):
    """批量生成人物参考图。"""
    total = len(character_ids)
    providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
    if not providers:
        raise ValueError("No AI provider found for image generation")

    adapter = providers[0]
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    size_map = {"9:16": "1088x1920", "16:9": "1920x1088", "1:1": "1440x1440"}
    size = size_map.get(aspect_ratio, "1088x1920")

    completed = 0
    for char_id in character_ids:
        try:
            with get_sync_session() as session:
                character = session.get(Character, char_id)
                if not character:
                    completed += 1
                    continue

                # 构建/使用提示词
                if character.reference_prompt_cn:
                    prompt = character.reference_prompt_cn
                else:
                    prompt = _build_char_prompt(character, aspect_ratio)
                    character.reference_prompt_cn = prompt

                request = AIRequest(
                    prompt=prompt,
                    service_type=ServiceType.TEXT_TO_IMAGE,
                    params={"size": size},
                )

                response = run_async(adapter.generate(request))

                if response.success and response.data:
                    image_data = response.data
                    if "url" in image_data or "image_url" in image_data:
                        import httpx
                        img_url = image_data.get("url") or image_data.get("image_url")
                        img_resp = httpx.get(img_url, timeout=60)
                        filename = f"char_{char_id}_{int(time.time())}.png"
                        filepath = upload_dir / filename
                        filepath.write_bytes(img_resp.content)
                        character.reference_image_path = str(filepath)
                    elif "base64" in image_data or "image_b64" in image_data:
                        import base64
                        b64_data = image_data.get("base64") or image_data.get("image_b64")
                        filename = f"char_{char_id}_{int(time.time())}.png"
                        filepath = upload_dir / filename
                        filepath.write_bytes(base64.b64decode(b64_data))
                        character.reference_image_path = str(filepath)
                    elif "local_path" in image_data:
                        character.reference_image_path = image_data["local_path"]

                    logger.info(f"Character image generated: {char_id}")
                else:
                    logger.error(f"Character image generation failed for {char_id}: {response.error}")

        except Exception as e:
            logger.error(f"Error generating image for character {char_id}: {e}")

        completed += 1
        progress = int(completed / total * 100)
        self.update_progress(workflow_step_id, progress, f"已完成 {completed}/{total} 个人物图片")

    logger.info(f"Character image generation complete: {completed}/{total} for project {project_id}")


def _find_char_ref_for_shot(shot: Shot, char_ref_map: dict[str, str]) -> str | None:
    """从镜头描述/幕名中匹配人物名称，返回对应的参照图 base64（带 data URI 前缀）。"""
    text = f"{shot.description or ''} {shot.act_name or ''}"
    import base64
    for name, ref_path in char_ref_map.items():
        if name in text:
            p = Path(ref_path)
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                return b64
    return None


# ─── Image Generation ────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.generate_images_for_shots")
def generate_images_for_shots(
    self,
    shot_ids: list[int],
    project_id: int,
    provider: str | None,
    model: str | None,
    workflow_step_id: int,
):
    """Generate images for a list of shots using the specified AI provider."""
    total = len(shot_ids)

    # 预加载人物参照图映射 {name: image_path}
    char_ref_map: dict[str, str] = {}
    with get_sync_session() as session:
        char_result = session.execute(
            select(Character).where(Character.project_id == project_id)
        )
        for c in char_result.scalars().all():
            if c.reference_image_path:
                char_ref_map[c.name] = c.reference_image_path

    adapter = registry.get_provider(provider) if provider else None

    if not adapter:
        # Try to find any provider that supports text-to-image
        providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError(f"No AI provider found for image generation (requested: {provider})")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for shot_id in shot_ids:
        try:
            with get_sync_session() as session:
                shot = session.get(Shot, shot_id)
                if not shot or shot.image_status != "pending":
                    completed += 1
                    continue

                prompt = shot.image_prompt or shot.description
                if not prompt:
                    shot.image_status = "skipped"
                    completed += 1
                    continue

                # 查找匹配的人物参照图
                ref_image_b64 = _find_char_ref_for_shot(shot, char_ref_map)

                service_type = ServiceType.TEXT_TO_IMAGE
                if ref_image_b64:
                    service_type = ServiceType.IMAGE_TO_IMAGE

                request = AIRequest(
                    prompt=prompt,
                    service_type=service_type,
                    model=model,
                    image_base64=ref_image_b64,
                )

                response = run_async(adapter.generate(request))

                if response.success and response.data:
                    # Save image data
                    image_data = response.data
                    saved = False
                    if "url" in image_data or "image_url" in image_data:
                        import httpx
                        img_url = image_data.get("url") or image_data.get("image_url")
                        img_resp = httpx.get(img_url, timeout=60)
                        filename = f"shot_{shot_id}_{int(time.time())}.png"
                        filepath = upload_dir / filename
                        filepath.write_bytes(img_resp.content)
                        shot.image_path = str(filepath)
                        saved = True
                    elif "base64" in image_data or "image_b64" in image_data:
                        import base64
                        b64_data = image_data.get("base64") or image_data.get("image_b64")
                        filename = f"shot_{shot_id}_{int(time.time())}.png"
                        filepath = upload_dir / filename
                        filepath.write_bytes(base64.b64decode(b64_data))
                        shot.image_path = str(filepath)
                        saved = True
                    elif "local_path" in image_data:
                        shot.image_path = image_data["local_path"]
                        saved = True

                    if saved:
                        shot.image_status = "completed"
                        shot.image_task_id = response.task_id
                        logger.info(f"Image saved for shot {shot_id}: {shot.image_path}")
                    else:
                        shot.image_status = "failed"
                        logger.error(f"Shot {shot_id}: unknown image data format: {list(image_data.keys())}")
                else:
                    shot.image_status = "failed"
                    error_msg = response.error or "Unknown error"
                    logger.error(f"Image generation failed for shot {shot_id}: {error_msg}")

            completed += 1
            progress = int(completed / total * 100)
            self.update_progress(workflow_step_id, progress, f"Completed {completed}/{total} images")

        except Exception as e:
            logger.error(f"Error generating image for shot {shot_id}: {e}")
            try:
                with get_sync_session() as session:
                    shot = session.get(Shot, shot_id)
                    if shot:
                        shot.image_status = "failed"
            except Exception:
                pass
            completed += 1

    logger.info(f"Image generation complete: {completed}/{total} shots for project {project_id}")


# ─── Video Generation ────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.generate_videos_for_shots")
def generate_videos_for_shots(
    self,
    shot_ids: list[int],
    project_id: int,
    provider: str | None,
    model: str | None,
    workflow_step_id: int,
):
    """Generate videos for a list of shots using the specified AI provider."""
    total = len(shot_ids)
    adapter = registry.get_provider(provider) if provider else None

    if not adapter:
        providers = registry.get_providers_for_service(ServiceType.IMAGE_TO_VIDEO)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError(f"No AI provider found for video generation (requested: {provider})")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for shot_id in shot_ids:
        try:
            with get_sync_session() as session:
                shot = session.get(Shot, shot_id)
                if not shot or shot.video_status != "pending":
                    completed += 1
                    continue

                prompt = shot.video_prompt or shot.description
                image_path = shot.image_path
                if not prompt:
                    shot.video_status = "skipped"
                    completed += 1
                    continue

                # 读取本地图片，转为 JPEG base64 data URI 传给大模型 API
                # 注意：万相 API 不支持带 alpha channel 的 PNG，统一转 JPEG
                import base64
                image_url = None
                if image_path:
                    p = Path(image_path)
                    if p.exists():
                        img_bytes = p.read_bytes()
                        # 尝试用 PIL 转 JPEG（去除 alpha channel，缩小体积）
                        try:
                            from io import BytesIO
                            from PIL import Image
                            img = Image.open(BytesIO(img_bytes))
                            if img.mode in ("RGBA", "P", "LA"):
                                img = img.convert("RGB")
                            buf = BytesIO()
                            img.save(buf, format="JPEG", quality=95)
                            img_bytes = buf.getvalue()
                        except ImportError:
                            pass
                        b64 = base64.b64encode(img_bytes).decode()
                        image_url = f"data:image/jpeg;base64,{b64}"
                        logger.info(f"Loaded image for shot {shot_id}: {p.name} -> JPEG data URI ({len(b64)} chars)")

                if not image_url:
                    logger.warning(f"Shot {shot_id}: no image available, skipping video generation")
                    shot.video_status = "failed"
                    completed += 1
                    continue

                request = AIRequest(
                    prompt=prompt,
                    service_type=ServiceType.IMAGE_TO_VIDEO,
                    model=model,
                    image_url=image_url,
                )

                response = run_async(adapter.generate(request))

                # 异步适配器：初始提交返回 task_id，需要轮询等待结果
                if response.task_id and hasattr(adapter, 'check_task'):
                    shot.video_task_id = response.task_id
                    shot.video_status = "processing"
                    session.commit()

                    max_wait = 600
                    interval = 10
                    elapsed = 0

                    while elapsed < max_wait:
                        time.sleep(interval)
                        elapsed += interval

                        poll = run_async(adapter.check_task(response.task_id))
                        if poll.success and poll.data:
                            status = poll.data.get("status", "").lower()
                            if status in ("completed", "succeeded"):
                                _save_video_result(shot_id, poll.data, upload_dir)
                                break
                            elif status == "failed":
                                _mark_video_failed(shot_id, poll.data.get("error", "Async task failed"))
                                break
                        elif not poll.success:
                            _mark_video_failed(shot_id, poll.error or "Poll failed")
                            break
                    else:
                        _mark_video_failed(shot_id, "Timeout waiting for video generation")

                elif response.success and response.data:
                    _save_video_result(shot_id, response.data, upload_dir)
                else:
                    _mark_video_failed(shot_id, response.error or "Unknown error")

            completed += 1
            progress = int(completed / total * 100)
            self.update_progress(workflow_step_id, progress, f"Completed {completed}/{total} videos")

        except Exception as e:
            logger.error(f"Error generating video for shot {shot_id}: {e}")
            _mark_video_failed(shot_id, str(e))
            completed += 1

    logger.info(f"Video generation complete: {completed}/{total} shots for project {project_id}")


def _save_video_result(shot_id: int, data: dict, upload_dir: Path):
    """Save video file from AI response to disk and update shot."""
    with get_sync_session() as session:
        shot = session.get(Shot, shot_id)
        if not shot:
            return

        saved = False
        video_url = data.get("url") or data.get("video_url")
        if video_url:
            import httpx

            vid_resp = httpx.get(video_url, timeout=120)
            filename = f"shot_{shot_id}_video_{int(time.time())}.mp4"
            filepath = upload_dir / filename
            filepath.write_bytes(vid_resp.content)
            shot.video_path = str(filepath)
            saved = True
        elif "local_path" in data:
            shot.video_path = data["local_path"]
            saved = True

        if saved:
            shot.video_status = "completed"
            logger.info(f"Video saved for shot {shot_id}: {shot.video_path}")
        else:
            shot.video_status = "failed"
            logger.error(f"Shot {shot_id}: no video URL/path in response data: {list(data.keys())}")


def _mark_video_failed(shot_id: int, error: str):
    """Mark a shot's video as failed."""
    try:
        with get_sync_session() as session:
            shot = session.get(Shot, shot_id)
            if shot:
                shot.video_status = "failed"
    except Exception as e:
        logger.error(f"Failed to mark shot {shot_id} video as failed: {e}")


# ─── Video Merge ─────────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.merge_project_videos")
def merge_project_videos(
    self,
    project_id: int,
    add_music: bool,
    music_path: str | None,
    workflow_step_id: int,
    shot_ids: list[int] | None = None,
):
    """Merge completed shot videos into a final project video."""
    from app.services.video_merge_service import VideoMergeService

    service = VideoMergeService()
    service.merge_project_videos(
        project_id=project_id,
        add_music=add_music,
        music_path=music_path,
        shot_ids=shot_ids,
        on_progress=lambda p, m: self.update_progress(workflow_step_id, p, m),
    )
