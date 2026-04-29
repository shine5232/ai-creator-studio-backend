"""Celery tasks for image/video generation and video merging."""

import json
import time
from pathlib import Path

from sqlalchemy import select

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.ai_gateway.user_config_resolver import resolve_user_config
from app.models.character import Character
from app.models.character import CharacterReferenceImage
from app.models.script import Script, Shot, Storyboard
from app.utils.logger import logger
from app.worker.celery_app import celery_app
from app.worker.db import get_sync_session
from app.worker.tasks.base import BaseWorkflowTask, run_async


# ─── User config resolver helper ─────────────────────────────────────────────

def _resolve_overrides(session, user_id: int | None, service_type: str) -> dict:
    """Resolve user config overrides.

    Returns dict with override_api_key, override_base_url, override_provider, override_model,
    and _adapter_config (to be merged into request.params).
    """
    if not user_id:
        return {}
    creds = resolve_user_config(session, user_id, service_type)
    if not creds:
        return {}
    overrides = {}
    if creds.api_key:
        overrides["override_api_key"] = creds.api_key
    if creds.base_url:
        overrides["override_base_url"] = creds.base_url
    if creds.provider:
        overrides["override_provider"] = creds.provider
    if creds.model_id:
        overrides["override_model"] = creds.model_id
    if creds.extra_config:
        overrides["_adapter_config"] = creds.extra_config
    return overrides


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
    prompt = (
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
        f"- 氛围：{mood or '未指定'}\n"
    )
    if shot.dialog:
        _lang_names = {"zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", "th": "泰语", "vi": "越南语", "fr": "法语", "de": "德语", "es": "西班牙语"}
        _lang_name = _lang_names.get(shot.dialog_lang or "zh", "中文")
        prompt += (
            f"- 台词：角色用{_lang_name}说\"{shot.dialog}\"\n"
            f"注意：图生视频提示词需要体现角色正在说话的状态，口型应匹配{_lang_name}发音。\n"
        )
    prompt += (
        f"\n## 视觉风格参考\n{visual_style}\n\n"
        "请生成提示词："
    )
    return prompt


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
    user_id: int | None = None,
):
    """为每个分镜调用 AI 生成 Seedream 文生图提示词，保存到 shot.image_prompt。"""
    total = len(shot_ids)
    providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
    if not providers:
        raise ValueError("No text generation provider available")

    adapter = providers[0]
    completed = 0

    # Resolve user config overrides
    text_overrides = {}
    if user_id:
        with get_sync_session() as session:
            text_overrides = _resolve_overrides(session, user_id, "text_generation")

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
                **text_overrides,
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


def _generate_detailed_char_description_sync(
    character_id: int, text_overrides: dict,
) -> dict | None:
    """Sync version: generate detailed character description using AI (for Celery tasks)."""
    providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
    if not providers:
        return None
    adapter = providers[0]

    with get_sync_session() as session:
        character = session.get(Character, character_id)
        if not character:
            return None

        attr_parts = []
        if character.gender:
            attr_parts.append(f"性别: {character.gender}")
        if character.age:
            attr_parts.append(f"年龄: {character.age}岁")
        if character.nationality:
            attr_parts.append(f"国籍/种族: {character.nationality}")
        if character.skin_tone:
            attr_parts.append(f"肤色: {character.skin_tone}")
        if character.appearance:
            attr_parts.append(f"外貌: {character.appearance}")
        if character.ethnic_features:
            attr_parts.append(f"种族特征: {character.ethnic_features}")
        if character.clothing:
            attr_parts.append(f"穿着: {character.clothing}")
        if character.personality:
            attr_parts.append(f"性格: {character.personality}")
        attr_text = "\n".join(attr_parts)

        prompt = (
            f"你是一个专业的AI人物肖像描述专家。请根据以下人物基本信息，生成一份详细的人物肖像描述，"
            f"包含面容、发型、肤色质感、体型、独特标记、整体气质等细节。同时为该人物的4个角度"
            f"（正面/front、左侧/left、右侧/right、背面/back）各生成一段文生图提示词。\n\n"
            f"人物名称: {character.name}\n"
            f"基本信息:\n{attr_text}\n\n"
            f"请严格按照以下 JSON 格式返回（不要包含任何其他文字）:\n"
            f'{{\n'
            f'  "detailed_description": "一段详细的中文人物肖像描述，200-400字",\n'
            f'  "angle_prompts": {{\n'
            f'    "front": "正面全身/半身肖像文生图提示词，中文，包含面部细节、穿着、光影",\n'
            f'    "left": "左侧角度全身/半身肖像文生图提示词",\n'
            f'    "right": "右侧角度全身/半身肖像文生图提示词",\n'
            f'    "back": "背面全身肖像文生图提示词"\n'
            f'  }}\n'
            f'}}\n'
        )
        request = AIRequest(
            prompt=prompt,
            service_type=ServiceType.TEXT_GENERATION,
            params={"temperature": 0.7, "max_tokens": 2048},
            **text_overrides,
        )
        response = run_async(adapter.generate(request))
        if not response.success or not response.data:
            logger.warning(f"AI description generation failed for char {character_id}: {response.error}")
            return None

        text = response.data.get("text", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start:end])
        except json.JSONDecodeError:
            return None

        detailed_description = parsed.get("detailed_description", "")
        angle_prompts = parsed.get("angle_prompts", {})

        character.detailed_description = detailed_description

        for angle in ("front", "left", "right", "back"):
            prompt_cn = angle_prompts.get(angle, "")
            if not prompt_cn:
                continue
            result = session.execute(
                select(CharacterReferenceImage).where(
                    CharacterReferenceImage.character_id == character_id,
                    CharacterReferenceImage.angle == angle,
                )
            )
            ref_img = result.scalar_one_or_none()
            if ref_img:
                ref_img.prompt_cn = prompt_cn
                if ref_img.status != "completed":
                    ref_img.status = "pending"
            else:
                ref_img = CharacterReferenceImage(
                    character_id=character_id,
                    angle=angle,
                    prompt_cn=prompt_cn,
                    status="pending",
                )
                session.add(ref_img)

        session.commit()
        logger.info(f"[SyncDesc] Generated detailed description for character {character_id}")
        return {"detailed_description": detailed_description, "angle_prompts": angle_prompts}


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
    user_id: int | None = None,
):
    """批量生成人物参考图。"""
    total = len(character_ids)

    # Resolve user config overrides
    img_overrides = {}
    if user_id:
        with get_sync_session() as session:
            img_overrides = _resolve_overrides(session, user_id, "text_to_image")

    # Select adapter based on user config or fallback
    resolved_provider = img_overrides.pop("override_provider", None)
    resolved_model = img_overrides.pop("override_model", None)
    adapter_config = img_overrides.pop("_adapter_config", {})

    adapter = registry.get_provider(resolved_provider) if resolved_provider else None
    if not adapter:
        providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError("No AI provider found for image generation")

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
                    model=resolved_model,
                    params={"size": size, "adapter_config": adapter_config},
                    **img_overrides,
                )

                response = run_async(adapter.generate(request))

                # Async adapter: initial submit returns task_id, poll for result
                if response.task_id and hasattr(adapter, 'check_task'):
                    max_wait = 300
                    interval = 5
                    elapsed = 0
                    while elapsed < max_wait:
                        time.sleep(interval)
                        elapsed += interval
                        poll = run_async(adapter.check_task(response.task_id, request=request))
                        if poll.success and poll.data:
                            status = poll.data.get("status", "").lower()
                            if status in ("completed", "succeeded"):
                                image_url = poll.data.get("image_url") or poll.data.get("url")
                                if image_url:
                                    import httpx
                                    img_resp = httpx.get(image_url, timeout=60)
                                    filename = f"char_{char_id}_{int(time.time())}.png"
                                    filepath = upload_dir / filename
                                    filepath.write_bytes(img_resp.content)
                                    character.reference_image_path = str(filepath)
                                    logger.info(f"Character image generated (async): {char_id}")
                                break
                            elif status == "failed":
                                logger.error(f"Character image async task failed for {char_id}")
                                break
                        elif not poll.success:
                            logger.error(f"Character image poll failed for {char_id}: {poll.error}")
                            break
                    else:
                        logger.error(f"Character image timeout for {char_id}")
                elif response.success and response.data:
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


def _save_generated_image(image_data: dict, upload_dir: Path, filename: str) -> str | None:
    """Save generated image from AI response to disk, return file path or None."""
    if "url" in image_data or "image_url" in image_data:
        import httpx
        img_url = image_data.get("url") or image_data.get("image_url")
        img_resp = httpx.get(img_url, timeout=60)
        filepath = upload_dir / filename
        filepath.write_bytes(img_resp.content)
        return str(filepath)
    elif "base64" in image_data or "image_b64" in image_data:
        import base64
        b64_data = image_data.get("base64") or image_data.get("image_b64")
        filepath = upload_dir / filename
        filepath.write_bytes(base64.b64decode(b64_data))
        return str(filepath)
    elif "local_path" in image_data:
        return image_data["local_path"]
    return None


def _generate_single_image(adapter, prompt: str, resolved_model: str | None,
                           adapter_config: dict, img_overrides: dict,
                           upload_dir: Path, filename: str) -> str | None:
    """Generate a single image via adapter, handle sync/async, return saved file path."""
    request = AIRequest(
        prompt=prompt,
        service_type=ServiceType.TEXT_TO_IMAGE,
        model=resolved_model,
        params={"size": "1088x1920", "adapter_config": adapter_config},
        **img_overrides,
    )
    response = run_async(adapter.generate(request))

    # Async adapter: poll for result
    if response.task_id and hasattr(adapter, 'check_task'):
        max_wait = 300
        interval = 5
        elapsed = 0
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            poll = run_async(adapter.check_task(response.task_id, request=request))
            if poll.success and poll.data:
                status = poll.data.get("status", "").lower()
                if status in ("completed", "succeeded"):
                    image_url = poll.data.get("image_url") or poll.data.get("url")
                    if image_url:
                        import httpx
                        img_resp = httpx.get(image_url, timeout=60)
                        filepath = upload_dir / filename
                        filepath.write_bytes(img_resp.content)
                        return str(filepath)
                    break
                elif status == "failed":
                    return None
            elif not poll.success:
                return None
        return None

    # Sync adapter
    if response.success and response.data:
        return _save_generated_image(response.data, upload_dir, filename)
    return None


@celery_app.task(
    bind=True, base=BaseWorkflowTask,
    name="app.worker.tasks.generation.generate_character_multi_angle_images",
    soft_time_limit=1200, time_limit=1800,
)
def generate_character_multi_angle_images(
    self,
    character_ids: list[int],
    project_id: int,
    aspect_ratio: str = "9:16",
    workflow_step_id: int = 0,
    user_id: int | None = None,
):
    """为每个角色生成4个角度（front/left/right/back）的参照图。"""
    angles = ["front", "left", "right", "back"]
    total = len(character_ids) * len(angles)

    # Resolve user config overrides
    img_overrides = {}
    if user_id:
        with get_sync_session() as session:
            img_overrides = _resolve_overrides(session, user_id, "text_to_image")

    resolved_provider = img_overrides.pop("override_provider", None)
    resolved_model = img_overrides.pop("override_model", None)
    adapter_config = img_overrides.pop("_adapter_config", {})

    adapter = registry.get_provider(resolved_provider) if resolved_provider else None
    if not adapter:
        providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError("No AI provider found for image generation")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for char_id in character_ids:
        with get_sync_session() as session:
            char_result = session.execute(
                select(CharacterReferenceImage).where(
                    CharacterReferenceImage.character_id == char_id,
                )
            )
            ref_images = {r.angle: r for r in char_result.scalars().all()}

        for angle in angles:
            try:
                with get_sync_session() as session:
                    ref_img = session.execute(
                        select(CharacterReferenceImage).where(
                            CharacterReferenceImage.character_id == char_id,
                            CharacterReferenceImage.angle == angle,
                        )
                    ).scalar_one_or_none()

                    if not ref_img or ref_img.status == "completed":
                        completed += 1
                        continue

                    # Use angle-specific prompt, fallback to basic prompt
                    if ref_img.prompt_cn:
                        prompt = ref_img.prompt_cn
                    else:
                        character = session.get(Character, char_id)
                        prompt = _build_char_prompt(character, aspect_ratio)

                    ref_img.status = "processing"
                    session.commit()

                filename = f"char_{char_id}_{angle}_{int(time.time())}.png"
                saved_path = _generate_single_image(
                    adapter, prompt, resolved_model, adapter_config,
                    img_overrides, upload_dir, filename,
                )

                with get_sync_session() as session:
                    ref_img = session.execute(
                        select(CharacterReferenceImage).where(
                            CharacterReferenceImage.character_id == char_id,
                            CharacterReferenceImage.angle == angle,
                        )
                    ).scalar_one_or_none()
                    if ref_img:
                        if saved_path:
                            ref_img.image_path = saved_path
                            ref_img.status = "completed"
                        else:
                            ref_img.status = "failed"
                        session.commit()

                    # Backward compat: set front image as character.reference_image_path
                    if saved_path and angle == "front":
                        character = session.get(Character, char_id)
                        if character:
                            character.reference_image_path = saved_path
                            session.commit()

            except Exception as e:
                logger.error(f"Error generating {angle} image for character {char_id}: {e}")
                try:
                    with get_sync_session() as session:
                        ref_img = session.execute(
                            select(CharacterReferenceImage).where(
                                CharacterReferenceImage.character_id == char_id,
                                CharacterReferenceImage.angle == angle,
                            )
                        ).scalar_one_or_none()
                        if ref_img:
                            ref_img.status = "failed"
                            session.commit()
                except Exception:
                    pass

            completed += 1
            progress = int(completed / total * 100)
            self.update_progress(workflow_step_id, progress, f"已完成 {completed}/{total} 个人物角度图片")

    logger.info(f"Multi-angle character image generation complete: {completed}/{total} for project {project_id}")


def _find_char_refs_for_shot(
    shot: Shot,
    char_ref_map: dict[str, dict[str, str]],
    legacy_char_ref_map: dict[str, str] | None = None,
) -> list[str]:
    """从 shot.characters 字段或文本中匹配人物名称，返回所有匹配的参照图 base64 列表。

    char_ref_map: {name: {angle: path}} — 多角度参照图映射
    legacy_char_ref_map: {name: path} — 旧版单图 fallback

    优先使用 shot.character_angles 指定角度，fallback 到 front → 任意可用角度。
    """
    import base64

    def _load_ref(ref_path: str) -> str | None:
        p = Path(ref_path)
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
        return None

    def _pick_best_ref(name: str) -> str | None:
        """Pick the best reference image for a character, respecting angle preference."""
        # Parse character_angles to find this character's preferred angle
        preferred_angle = None
        if shot.character_angles:
            for entry in shot.character_angles.split(","):
                entry = entry.strip()
                if ":" in entry:
                    char_name, angle = entry.split(":", 1)
                    if char_name.strip() == name:
                        preferred_angle = angle.strip()
                        break

        angle_map = char_ref_map.get(name)
        if angle_map:
            # Priority: specified angle → front → any available
            if preferred_angle and preferred_angle in angle_map:
                return angle_map[preferred_angle]
            if "front" in angle_map:
                return angle_map["front"]
            for path in angle_map.values():
                return path  # first available

        # Legacy fallback
        if legacy_char_ref_map:
            return legacy_char_ref_map.get(name)

        return None

    matched: list[str] = []

    # 1. Prefer shot.characters field
    if shot.characters:
        for name in shot.characters.split(","):
            name = name.strip()
            if not name:
                continue
            ref_path = _pick_best_ref(name)
            if ref_path:
                b64 = _load_ref(ref_path)
                if b64:
                    matched.append(b64)
            else:
                # Alias matching
                for map_name, angle_map in char_ref_map.items():
                    if name in map_name or map_name in name:
                        # Try front first, then any
                        path = angle_map.get("front") or next(iter(angle_map.values()), None)
                        if path:
                            b64 = _load_ref(path)
                            if b64:
                                matched.append(b64)
                                break
                if not matched:
                    if legacy_char_ref_map:
                        for map_name, map_path in legacy_char_ref_map.items():
                            if name in map_name or map_name in name:
                                b64 = _load_ref(map_path)
                                if b64:
                                    matched.append(b64)
                                    break

    # 2. Fallback: match from description text
    if not matched:
        text = f"{shot.description or ''} {shot.act_name or ''}"
        for name, angle_map in char_ref_map.items():
            if name in text:
                path = angle_map.get("front") or next(iter(angle_map.values()), None)
                if path:
                    b64 = _load_ref(path)
                    if b64:
                        matched.append(b64)
        if not matched and legacy_char_ref_map:
            for name, ref_path in legacy_char_ref_map.items():
                if name in text:
                    b64 = _load_ref(ref_path)
                    if b64:
                        matched.append(b64)

    return matched


# ─── Image Generation ────────────────────────────────────────────────────────


@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.worker.tasks.generation.generate_images_for_shots")
def generate_images_for_shots(
    self,
    shot_ids: list[int],
    project_id: int,
    provider: str | None,
    model: str | None,
    workflow_step_id: int,
    user_id: int | None = None,
):
    """Generate images for a list of shots using the specified AI provider."""
    total = len(shot_ids)

    # Resolve user config overrides
    img_overrides = {}
    if user_id:
        with get_sync_session() as session:
            img_overrides = _resolve_overrides(session, user_id, "text_to_image")

    # Extract provider/model from user config for adapter routing
    resolved_provider = provider or img_overrides.pop("override_provider", None)
    resolved_model = model or img_overrides.pop("override_model", None)
    shot_adapter_config = img_overrides.pop("_adapter_config", {})

    # 预加载人物参照图映射 {name: {angle: path}}
    char_ref_map: dict[str, dict[str, str]] = {}
    legacy_char_ref_map: dict[str, str] = {}
    with get_sync_session() as session:
        char_result = session.execute(
            select(Character).where(Character.project_id == project_id)
        )
        for c in char_result.scalars().all():
            if c.reference_image_path:
                legacy_char_ref_map[c.name] = c.reference_image_path
            # Build angle map from CharacterReferenceImage records
            angle_map: dict[str, str] = {}
            for ref in c.reference_images:
                if ref.image_path and ref.status == "completed":
                    angle_map[ref.angle] = ref.image_path
            if angle_map:
                char_ref_map[c.name] = angle_map

    adapter = registry.get_provider(resolved_provider) if resolved_provider else None

    if not adapter:
        # Try to find any provider that supports text-to-image
        providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
        if providers:
            adapter = providers[0]
        else:
            raise ValueError(f"No AI provider found for image generation (requested: {resolved_provider})")

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

                # 查找匹配的人物参照图（支持多人物，角度感知）
                ref_images_b64 = _find_char_refs_for_shot(shot, char_ref_map, legacy_char_ref_map)
                ref_image_b64 = None
                if ref_images_b64:
                    service_type = ServiceType.IMAGE_TO_IMAGE
                    # 取第一个参考图作为主参考（后续可通过 image_urls 传递多个）
                    ref_image_b64 = ref_images_b64[0]

                request = AIRequest(
                    prompt=prompt,
                    service_type=service_type,
                    model=resolved_model,
                    image_base64=ref_image_b64,
                    params={
                        "adapter_config": shot_adapter_config,
                        "extra_ref_images": ref_images_b64[1:] if len(ref_images_b64) > 1 else [],
                    },
                    **img_overrides,
                )

                response = run_async(adapter.generate(request))

                # Async adapter: initial submit returns task_id, poll for result
                if response.task_id and hasattr(adapter, 'check_task'):
                    shot.image_task_id = response.task_id
                    shot.image_status = "processing"
                    session.commit()

                    max_wait = 300
                    interval = 5
                    elapsed = 0
                    while elapsed < max_wait:
                        time.sleep(interval)
                        elapsed += interval
                        poll = run_async(adapter.check_task(response.task_id, request=request))
                        if poll.success and poll.data:
                            status = poll.data.get("status", "").lower()
                            if status in ("completed", "succeeded"):
                                image_url = poll.data.get("image_url") or poll.data.get("url")
                                if image_url:
                                    import httpx
                                    img_resp = httpx.get(image_url, timeout=60)
                                    filename = f"shot_{shot_id}_{int(time.time())}.png"
                                    filepath = upload_dir / filename
                                    filepath.write_bytes(img_resp.content)
                                    shot.image_path = str(filepath)
                                    shot.image_status = "completed"
                                    shot.image_task_id = response.task_id
                                    logger.info(f"Image saved for shot {shot_id} (async): {shot.image_path}")
                                break
                            elif status == "failed":
                                shot.image_status = "failed"
                                logger.error(f"Shot {shot_id}: async image task failed")
                                break
                        elif not poll.success:
                            shot.image_status = "failed"
                            logger.error(f"Shot {shot_id}: poll failed: {poll.error}")
                            break
                    else:
                        shot.image_status = "failed"
                        logger.error(f"Shot {shot_id}: timeout waiting for image generation")

                elif response.success and response.data:
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
    user_id: int | None = None,
):
    """Generate videos for a list of shots using the specified AI provider."""
    total = len(shot_ids)

    # Resolve user config overrides
    vid_overrides = {}
    if user_id:
        with get_sync_session() as session:
            vid_overrides = _resolve_overrides(session, user_id, "image_to_video")

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

                # Inject dialog language info for lip-sync
                if shot.dialog:
                    _lang_names = {"zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", "th": "泰语", "vi": "越南语", "fr": "法语", "de": "德语", "es": "西班牙语"}
                    _lang_name = _lang_names.get(shot.dialog_lang or "zh", "中文")
                    prompt = f"角色正在用{_lang_name}说话\"{shot.dialog}\"，口型匹配{_lang_name}发音。{prompt}"
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
                    **vid_overrides,
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


# ─── Auto-Generate Pipeline (一键爆款) ───────────────────────────────────────


def _calc_progress(step_start: int, step_end: int, completed: int, total: int) -> int:
    """Calculate progress within a step's percentage range."""
    if total == 0:
        return step_end
    return int(step_start + (step_end - step_start) * (completed / total))


@celery_app.task(
    bind=True, base=BaseWorkflowTask,
    name="app.worker.tasks.generation.auto_generate_pipeline",
    soft_time_limit=1800, time_limit=2400,
)
def auto_generate_pipeline(
    self,
    project_id: int,
    script_params: dict,
    workflow_step_id: int,
    user_id: int | None = None,
):
    """一键爆款：从空白项目自动完成 脚本→人物提示词→分镜提示词→人物图→分镜图→分镜视频→合成。"""

    # Pre-resolve all user config overrides
    auto_text_overrides = {}
    auto_img_overrides = {}
    auto_vid_overrides = {}
    if user_id:
        with get_sync_session() as session:
            auto_text_overrides = _resolve_overrides(session, user_id, "text_generation")
            auto_img_overrides = _resolve_overrides(session, user_id, "text_to_image")
            auto_vid_overrides = _resolve_overrides(session, user_id, "image_to_video")

    # ── Step 1: AI 生成脚本 (0% → 10%) ──────────────────────────────────────
    self.update_progress(workflow_step_id, 0, "步骤 1/7: 正在生成脚本...")
    try:
        from app.database import async_session_maker
        from app.services.script_service import ScriptService
        from app.schemas.script import GenerateScriptRequest

        async def _gen_script():
            async with async_session_maker() as db:
                svc = ScriptService(db)
                req = GenerateScriptRequest(**script_params)
                return await svc.generate_script(project_id, req)

        script = run_async(_gen_script())
        logger.info(f"[AutoGenerate] Script generated: {script.id}")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 1 (script) failed: {e}")
        raise  # 脚本生成失败直接中断

    self.update_progress(workflow_step_id, 10, "步骤 1/7: 脚本生成完成")

    # ── Step 2: AI 生成详细人物描述 + 4角度提示词 (10% → 15%) ──────────────
    self.update_progress(workflow_step_id, 10, "步骤 2/7: 生成详细人物描述...")
    try:
        providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
        text_adapter = providers[0] if providers else None

        with get_sync_session() as session:
            result = session.execute(
                select(Character).where(Character.project_id == project_id)
            )
            chars_no_desc = [c for c in result.scalars().all() if not c.detailed_description]

        if chars_no_desc and text_adapter:
            total_chars = len(chars_no_desc)
            for i, char in enumerate(chars_no_desc):
                try:
                    desc_result = _generate_detailed_char_description_sync(
                        char.id, auto_text_overrides,
                    )
                    if desc_result:
                        logger.info(f"[AutoGenerate] Detailed desc generated for char {char.id}")
                except Exception as e:
                    logger.warning(f"[AutoGenerate] Detailed desc failed for {char.id}: {e}")

                prog = _calc_progress(10, 15, i + 1, total_chars)
                self.update_progress(workflow_step_id, prog, f"步骤 2/7: 人物描述 {i+1}/{total_chars}")
        else:
            logger.info("[AutoGenerate] Step 2 skipped: all characters have descriptions or no text provider")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 2 failed (non-fatal): {e}")

    self.update_progress(workflow_step_id, 15, "步骤 2/7: 人物提示词完成")

    # ── Step 3: 补全分镜提示词 (15% → 20%) ──────────────────────────────────
    self.update_progress(workflow_step_id, 15, "步骤 3/7: 检查分镜提示词...")
    try:
        with get_sync_session() as session:
            # 获取该项目的所有 shot
            shots_result = session.execute(
                select(Shot)
                .join(Storyboard, Shot.storyboard_id == Storyboard.id)
                .join(Script, Storyboard.script_id == Script.id)
                .where(Script.project_id == project_id)
                .order_by(Shot.shot_number)
            )
            all_shots = list(shots_result.scalars().all())
            shots_no_prompt = [s for s in all_shots if not s.image_prompt or not s.video_prompt]

        if shots_no_prompt and text_adapter:
            # 加载辅助数据
            with get_sync_session() as session:
                storyboard = session.get(Storyboard, shots_no_prompt[0].storyboard_id)
                script_obj = session.get(Script, storyboard.script_id) if storyboard else None
                script_title = script_obj.title if script_obj else "未知"
                char_profiles_text = (
                    _build_character_profiles_text(
                        script_obj.content, project_id=project_id, session=session
                    ) if script_obj else ""
                )
                # 视觉风格
                visual_style = ""
                marker = "---STRUCTURED_DATA---"
                if script_obj and marker in script_obj.content:
                    try:
                        parts = script_obj.content.split(marker, 1)
                        structured = json.loads(parts[1].strip())
                        vd = structured.get("visual_design", {})
                        style_parts = []
                        if vd.get("color_progression"):
                            style_parts.append(f"色调变化：{vd['color_progression']}")
                        for s in vd.get("visual_symbols", []):
                            style_parts.append(f"视觉符号：{s.get('symbol', '')}({s.get('meaning', '')})")
                        visual_style = "\n".join(style_parts)
                    except json.JSONDecodeError:
                        pass

            total_shots = len(shots_no_prompt)
            for i, shot in enumerate(shots_no_prompt):
                try:
                    prompt = _build_prompt_for_shot(
                        shot, char_profiles_text, script_title,
                        shot.tone, shot.mood, visual_style,
                    )
                    request = AIRequest(
                        prompt=prompt,
                        service_type=ServiceType.TEXT_GENERATION,
                        params={"temperature": 0.7, "max_tokens": 1024},
                        **auto_text_overrides,
                    )
                    response = run_async(text_adapter.generate(request))
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
                except Exception as e:
                    logger.warning(f"[AutoGenerate] Shot prompt failed for {shot.id}: {e}")

                prog = _calc_progress(15, 20, i + 1, total_shots)
                self.update_progress(workflow_step_id, prog, f"步骤 3/7: 分镜提示词 {i+1}/{total_shots}")
        else:
            logger.info("[AutoGenerate] Step 3 skipped: all shots have prompts")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 3 failed (non-fatal): {e}")

    self.update_progress(workflow_step_id, 20, "步骤 3/7: 分镜提示词完成")

    # ── Step 4: 生成人物多角度参照图片 (20% → 35%) ─────────────────────────
    self.update_progress(workflow_step_id, 20, "步骤 4/7: 正在生成人物多角度参照图片...")
    try:
        # Extract provider/model from user config for adapter routing
        auto_img_provider = auto_img_overrides.pop("override_provider", None)
        auto_img_model = auto_img_overrides.pop("override_model", None)
        auto_img_adapter_config = auto_img_overrides.pop("_adapter_config", {})

        img_adapter = registry.get_provider(auto_img_provider) if auto_img_provider else None
        if not img_adapter:
            img_providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
            img_adapter = img_providers[0] if img_providers else None

        if img_adapter:
            angles = ["front", "left", "right", "back"]
            with get_sync_session() as session:
                result = session.execute(
                    select(Character).where(Character.project_id == project_id)
                )
                characters = list(result.scalars().all())
                # Filter to characters that have pending reference images
                char_ids_needing_images = []
                for c in characters:
                    if not c.reference_image_path:
                        char_ids_needing_images.append(c.id)
                        continue
                    # Check if multi-angle images exist
                    completed_angles = [
                        r.angle for r in c.reference_images
                        if r.status == "completed" and r.image_path
                    ]
                    if len(completed_angles) < 4:
                        char_ids_needing_images.append(c.id)

            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            total_items = len(char_ids_needing_images) * 4  # 4 angles per character
            completed = 0

            for char_id in char_ids_needing_images:
                for angle in angles:
                    try:
                        with get_sync_session() as session:
                            ref_img = session.execute(
                                select(CharacterReferenceImage).where(
                                    CharacterReferenceImage.character_id == char_id,
                                    CharacterReferenceImage.angle == angle,
                                )
                            ).scalar_one_or_none()

                            if ref_img and ref_img.status == "completed" and ref_img.image_path:
                                completed += 1
                                continue

                            # Get prompt
                            if ref_img and ref_img.prompt_cn:
                                prompt = ref_img.prompt_cn
                            else:
                                character = session.get(Character, char_id)
                                prompt = _build_char_prompt(character)

                            if ref_img:
                                ref_img.status = "processing"
                                session.commit()

                        filename = f"char_{char_id}_{angle}_{int(time.time())}.png"
                        saved_path = _generate_single_image(
                            img_adapter, prompt, auto_img_model, auto_img_adapter_config,
                            auto_img_overrides, upload_dir, filename,
                        )

                        with get_sync_session() as session:
                            ref_img = session.execute(
                                select(CharacterReferenceImage).where(
                                    CharacterReferenceImage.character_id == char_id,
                                    CharacterReferenceImage.angle == angle,
                                )
                            ).scalar_one_or_none()

                            if saved_path:
                                if not ref_img:
                                    ref_img = CharacterReferenceImage(
                                        character_id=char_id,
                                        angle=angle,
                                        image_path=saved_path,
                                        status="completed",
                                    )
                                    session.add(ref_img)
                                else:
                                    ref_img.image_path = saved_path
                                    ref_img.status = "completed"

                                # Backward compat for front angle
                                if angle == "front":
                                    character = session.get(Character, char_id)
                                    if character:
                                        character.reference_image_path = saved_path
                            else:
                                if ref_img:
                                    ref_img.status = "failed"
                            session.commit()

                    except Exception as e:
                        logger.error(f"[AutoGenerate] Char {char_id} angle {angle} error: {e}")

                    completed += 1
                    if total_items > 0:
                        prog = _calc_progress(20, 35, completed, total_items)
                        self.update_progress(workflow_step_id, prog, f"步骤 4/7: 人物图片 {completed}/{total_items}")
        else:
            logger.warning("[AutoGenerate] Step 4 skipped: no TEXT_TO_IMAGE provider")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 4 failed (non-fatal): {e}")

    self.update_progress(workflow_step_id, 35, "步骤 4/7: 人物图片完成")

    # ── Step 5: 生成分镜图片 (35% → 60%) ────────────────────────────────────
    self.update_progress(workflow_step_id, 35, "步骤 5/7: 正在生成分镜图片...")
    try:
        # 收集 shot_ids
        with get_sync_session() as session:
            shots_result = session.execute(
                select(Shot)
                .join(Storyboard, Shot.storyboard_id == Storyboard.id)
                .join(Script, Storyboard.script_id == Script.id)
                .where(Script.project_id == project_id)
                .where(Shot.image_status == "pending")
                .order_by(Shot.shot_number)
            )
            pending_image_shots = list(shots_result.scalars().all())

        if pending_image_shots:
            shot_ids = [s.id for s in pending_image_shots]
            total = len(shot_ids)

            # 复用 generate_images_for_shots 的内部逻辑（角度感知）
            char_ref_map: dict[str, dict[str, str]] = {}
            legacy_char_ref_map: dict[str, str] = {}
            with get_sync_session() as session:
                char_result = session.execute(
                    select(Character).where(Character.project_id == project_id)
                )
                for c in char_result.scalars().all():
                    if c.reference_image_path:
                        legacy_char_ref_map[c.name] = c.reference_image_path
                    angle_map: dict[str, str] = {}
                    for ref in c.reference_images:
                        if ref.image_path and ref.status == "completed":
                            angle_map[ref.angle] = ref.image_path
                    if angle_map:
                        char_ref_map[c.name] = angle_map

            adapter = img_adapter or (registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE) or [None])[0]
            if not adapter:
                raise ValueError("No TEXT_TO_IMAGE provider available")

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
                        ref_images_b64 = _find_char_refs_for_shot(shot, char_ref_map, legacy_char_ref_map)
                        ref_image_b64 = ref_images_b64[0] if ref_images_b64 else None
                        service_type = ServiceType.IMAGE_TO_IMAGE if ref_image_b64 else ServiceType.TEXT_TO_IMAGE
                        request = AIRequest(
                            prompt=prompt, service_type=service_type,
                            model=auto_img_model,
                            image_base64=ref_image_b64,
                            params={
                                "size": "1088x1920",
                                "adapter_config": auto_img_adapter_config,
                                "extra_ref_images": ref_images_b64[1:] if len(ref_images_b64) > 1 else [],
                            },
                            **auto_img_overrides,
                        )
                        response = run_async(adapter.generate(request))

                        # Async adapter: poll for result
                        if response.task_id and hasattr(adapter, 'check_task'):
                            shot.image_task_id = response.task_id
                            shot.image_status = "processing"
                            session.commit()

                            max_wait = 300
                            interval = 5
                            elapsed = 0
                            while elapsed < max_wait:
                                time.sleep(interval)
                                elapsed += interval
                                poll = run_async(adapter.check_task(response.task_id, request=request))
                                if poll.success and poll.data:
                                    status = poll.data.get("status", "").lower()
                                    if status in ("completed", "succeeded"):
                                        image_url = poll.data.get("image_url") or poll.data.get("url")
                                        if image_url:
                                            import httpx
                                            img_resp = httpx.get(image_url, timeout=60)
                                            filename = f"shot_{shot_id}_{int(time.time())}.png"
                                            filepath = upload_dir / filename
                                            filepath.write_bytes(img_resp.content)
                                            shot.image_path = str(filepath)
                                            shot.image_status = "completed"
                                            shot.image_task_id = response.task_id
                                            logger.info(f"[AutoGenerate] Shot image saved (async): {shot_id}")
                                        break
                                    elif status == "failed":
                                        shot.image_status = "failed"
                                        break
                                elif not poll.success:
                                    shot.image_status = "failed"
                                    break
                            else:
                                shot.image_status = "failed"

                        elif response.success and response.data:
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
                            else:
                                shot.image_status = "failed"
                        else:
                            shot.image_status = "failed"
                except Exception as e:
                    logger.error(f"[AutoGenerate] Shot image error {shot_id}: {e}")
                    try:
                        with get_sync_session() as session:
                            shot = session.get(Shot, shot_id)
                            if shot:
                                shot.image_status = "failed"
                    except Exception:
                        pass
                completed += 1
                prog = _calc_progress(35, 60, completed, total)
                self.update_progress(workflow_step_id, prog, f"步骤 5/7: 分镜图片 {completed}/{total}")
        else:
            logger.info("[AutoGenerate] Step 5 skipped: no pending image shots")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 5 failed: {e}")

    self.update_progress(workflow_step_id, 60, "步骤 5/7: 分镜图片完成")

    # ── Step 6: 生成分镜短视频 (60% → 90%) ──────────────────────────────────
    self.update_progress(workflow_step_id, 60, "步骤 6/7: 正在生成分镜短视频...")
    try:
        with get_sync_session() as session:
            shots_result = session.execute(
                select(Shot)
                .join(Storyboard, Shot.storyboard_id == Storyboard.id)
                .join(Script, Storyboard.script_id == Script.id)
                .where(Script.project_id == project_id)
                .where(Shot.video_status == "pending")
                .order_by(Shot.shot_number)
            )
            pending_video_shots = list(shots_result.scalars().all())

        if pending_video_shots:
            shot_ids = [s.id for s in pending_video_shots]
            total = len(shot_ids)

            # Extract provider/model from user config for video adapter routing
            auto_vid_provider = auto_vid_overrides.pop("override_provider", None)
            auto_vid_model = auto_vid_overrides.pop("override_model", None)
            auto_vid_adapter_config = auto_vid_overrides.pop("_adapter_config", {})

            vid_adapter = registry.get_provider(auto_vid_provider) if auto_vid_provider else None
            if not vid_adapter:
                vid_providers = registry.get_providers_for_service(ServiceType.IMAGE_TO_VIDEO)
                vid_adapter = vid_providers[0] if vid_providers else None
            if not vid_adapter:
                raise ValueError("No IMAGE_TO_VIDEO provider available")

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
                        if not prompt or not image_path:
                            shot.video_status = "failed"
                            completed += 1
                            continue

                        # Inject dialog language info for lip-sync
                        if shot.dialog:
                            _lang_names = {"zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", "th": "泰语", "vi": "越南语", "fr": "法语", "de": "德语", "es": "西班牙语"}
                            _lang_name = _lang_names.get(shot.dialog_lang or "zh", "中文")
                            prompt = f"角色正在用{_lang_name}说话\"{shot.dialog}\"，口型匹配{_lang_name}发音。{prompt}"

                        # 读取图片转 JPEG base64
                        import base64
                        p = Path(image_path)
                        image_url = None
                        if p.exists():
                            img_bytes = p.read_bytes()
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

                        if not image_url:
                            shot.video_status = "failed"
                            completed += 1
                            continue

                        request = AIRequest(
                            prompt=prompt,
                            service_type=ServiceType.IMAGE_TO_VIDEO,
                            model=auto_vid_model,
                            image_url=image_url,
                            params={"adapter_config": auto_vid_adapter_config},
                            **auto_vid_overrides,
                        )
                        response = run_async(vid_adapter.generate(request))

                        # 异步适配器轮询
                        if response.task_id and hasattr(vid_adapter, 'check_task'):
                            shot.video_task_id = response.task_id
                            shot.video_status = "processing"
                            session.commit()
                            max_wait = 600
                            interval = 10
                            elapsed = 0
                            while elapsed < max_wait:
                                time.sleep(interval)
                                elapsed += interval
                                poll = run_async(vid_adapter.check_task(response.task_id))
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
                except Exception as e:
                    logger.error(f"[AutoGenerate] Shot video error {shot_id}: {e}")
                    _mark_video_failed(shot_id, str(e))

                completed += 1
                prog = _calc_progress(60, 90, completed, total)
                self.update_progress(workflow_step_id, prog, f"步骤 6/7: 分镜视频 {completed}/{total}")
        else:
            logger.info("[AutoGenerate] Step 6 skipped: no pending video shots")
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 6 failed: {e}")

    self.update_progress(workflow_step_id, 90, "步骤 6/7: 分镜视频完成")

    # ── Step 7: 合成短片 (90% → 100%) ───────────────────────────────────────
    self.update_progress(workflow_step_id, 90, "步骤 7/7: 正在合成短片...")
    try:
        from app.services.video_merge_service import VideoMergeService

        merge_service = VideoMergeService()
        merge_service.merge_project_videos(
            project_id=project_id,
            add_music=False,
            music_path=None,
            shot_ids=None,
            on_progress=lambda p, m: self.update_progress(
                workflow_step_id, _calc_progress(90, 100, p, 100), f"步骤 7/7: {m}"
            ),
        )
    except Exception as e:
        logger.error(f"[AutoGenerate] Step 7 (merge) failed: {e}")
        raise

    self.update_progress(workflow_step_id, 100, "一键生成完成！所有步骤已成功执行")
    logger.info(f"[AutoGenerate] Pipeline complete for project {project_id}")
