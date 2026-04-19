import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.models.script import Script, Storyboard, Shot
from app.schemas.storyboard import CreateStoryboardRequest, UpdateShotRequest
from app.utils.logger import logger


class StoryboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_storyboard(self, script_id: int) -> Storyboard | None:
        result = await self.db.execute(
            select(Storyboard).where(Storyboard.script_id == script_id)
        )
        return result.scalar_one_or_none()

    async def create_storyboard(self, script_id: int, data: CreateStoryboardRequest) -> Storyboard:
        script_result = await self.db.execute(select(Script).where(Script.id == script_id))
        script = script_result.scalar_one_or_none()
        if not script:
            raise ValueError("Script not found")

        # Check if storyboard already exists
        existing = await self.get_storyboard(script_id)
        if existing:
            # If storyboard already has shots (auto-created during script generation), return as-is
            if existing.shots:
                return existing
            # Otherwise update tone_mapping only
            if data.tone_mapping:
                existing.tone_mapping = json.dumps(data.tone_mapping)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Generate shots from script content using AI
        storyboard = Storyboard(
            script_id=script_id,
            total_shots=0,
            tone_mapping=json.dumps(data.tone_mapping) if data.tone_mapping else None,
        )
        self.db.add(storyboard)
        await self.db.flush()

        shots = await self._generate_shots_from_script(storyboard, script)
        storyboard.total_shots = len(shots)
        storyboard.total_duration = sum(s.video_duration for s in shots)

        await self.db.commit()
        await self.db.refresh(storyboard)
        logger.info(f"Storyboard created: {storyboard.id} with {len(shots)} shots for script {script_id}")
        return storyboard

    async def get_storyboard_detail(self, storyboard_id: int) -> Storyboard | None:
        result = await self.db.execute(
            select(Storyboard).where(Storyboard.id == storyboard_id)
        )
        return result.scalar_one_or_none()

    async def update_shot(self, shot_id: int, data: UpdateShotRequest) -> Shot:
        result = await self.db.execute(select(Shot).where(Shot.id == shot_id))
        shot = result.scalar_one_or_none()
        if not shot:
            raise ValueError("Shot not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(shot, field, value)

        await self.db.commit()
        await self.db.refresh(shot)
        return shot

    async def _generate_shots_from_script(self, storyboard: Storyboard, script: Script) -> list[Shot]:
        """Call GLM to break script content into storyboard shots."""
        providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
        if not providers:
            logger.warning("No text generation provider available, creating empty storyboard")
            return []

        adapter = providers[0]

        # 从脚本 content 中提取结构化场景/人物数据（如果存在）
        display_content = script.content
        scene_context = ""
        marker = "---STRUCTURED_DATA---"
        if marker in script.content:
            parts = script.content.split(marker, 1)
            display_content = parts[0].strip()
            try:
                structured = json.loads(parts[1].strip())
                character_profiles = structured.get("character_profiles", [])
                if character_profiles:
                    scene_context += "【人物设定】\n"
                    for cp in character_profiles:
                        clothing = ""
                        if cp.get("clothing_phases"):
                            clothing = "；".join(
                                f"{p.get('phase', '')}: {p.get('description', '')}"
                                for p in cp["clothing_phases"]
                            )
                        scene_context += (
                            f"  {cp.get('role_name', '角色')}: "
                            f"{cp.get('age', '')}岁{cp.get('gender', '')}，"
                            f"{cp.get('race_ethnicity', '')}，"
                            f"肤色{cp.get('skin_color', '')}，"
                            f"眼{cp.get('eyes', '')}，"
                            f"发型{cp.get('hair', '')}，"
                            f"{cp.get('facial_features', '')}，"
                            f"{cp.get('body_type', '')}"
                            + (f"；穿着变化: {clothing}" if clothing else "")
                            + "\n"
                        )
                    scene_context += "\n"

                acts_data = structured.get("acts", [])
                if acts_data:
                    scene_context += "【分镜结构】\n"
                    for act in acts_data:
                        scene_context += f"第{act.get('act_number', '?')}幕: {act.get('act_name', '')} ({act.get('time_range', '')})\n"
                        for shot in act.get("shots", []):
                            scene_context += (
                                f"  镜头{shot.get('shot_number', '?')} {shot.get('time_range', '')} "
                                f"[{shot.get('shot_type', '')}] {shot.get('location', '')}\n"
                                f"    人物: {shot.get('characters', '')}\n"
                                f"    环境: {shot.get('environment', '')}\n"
                                f"    事件: {shot.get('event', '')}\n"
                            )
                            scene_context += (
                                f"    色调: {shot.get('tone', '')} | 氛围: {shot.get('mood', '')}\n"
                            )
                    scene_context += "\n"

                vd = structured.get("visual_design", {})
                if vd:
                    if vd.get("color_progression"):
                        scene_context += f"【色调变化】{vd['color_progression']}\n"
                    if vd.get("visual_symbols"):
                        scene_context += "【视觉符号】" + "、".join(
                            f"{s['symbol']}({s['meaning']})" for s in vd["visual_symbols"]
                        ) + "\n"
            except json.JSONDecodeError:
                pass

        # 加载知识库参考：脚本级 source_case_id → 项目级 reference_case_id
        visual_reference = ""
        ref_case_id = script.source_case_id
        if not ref_case_id:
            from app.models.project import Project
            project = await self.db.get(Project, script.project_id)
            if project:
                ref_case_id = project.reference_case_id

        if ref_case_id:
            from app.services.knowledge_service import KnowledgeService
            ks = KnowledgeService(self.db)
            ref = await ks.get_reference_context(ref_case_id)
            if ref:
                chars_part = f"人物外貌特征: {ref['characters_ethnicity']}\n" if ref.get("characters_ethnicity") else ""
                visual_reference = (
                    f"\n\n【参考爆款案例视觉风格】\n"
                    f"案例: {ref['title']} (点赞率: {ref['like_rate']})\n"
                    f"视觉风格: {ref['visual_style']}\n"
                    f"情感曲线: {ref['emotion_curve']}\n"
                    f"视觉符号: {', '.join(ref['visual_symbols'])}\n"
                    f"{chars_part}"
                    f"请在生成 image_prompt 和 video_prompt 时参考以上视觉风格和人物外貌。"
                )

        duration_hint = ""
        if script.duration_seconds:
            duration_hint = f"目标总时长约{script.duration_seconds}秒。"

        prompt = (
            "你是一个专业的短视频分镜师。请根据以下脚本内容，将其拆分为多个镜头（shots），"
            "并以 JSON 数组格式返回。每个镜头包含以下字段：\n"
            "- act_name: 场幕名称（可选）\n"
            "- time_range: 时间范围，如 '0-3s'（可选）\n"
            "- shot_type: 镜头类型，如 close_up/medium/wide/establishing（可选）\n"
            "- description: 镜头画面描述（必填，中文，包含人物外貌、动作、环境细节）\n"
            "- tone: 画面色调（可选）\n"
            "- mood: 情绪氛围（可选）\n"
            "- image_prompt: Seedream文生图提示词（中文为主，专业术语用英文）\n"
            "  格式要求：先写画面内容（主体+行为+环境），再写美学短词（风格+色调+光影+构图）\n"
            "  可用美学词示例：电影感、高对比、暖色调、低饱和、胶片质感、黄金时段光线、轮廓光、丁达尔光\n"
            "  可用构图词示例：特写、近景、中景、大远景、仰视视角、俯视视角\n"
            "  可用风格词示例：纪实摄影、国家地理风格、港风、复古风、古风摄影、肖像摄影\n"
            "- video_prompt: 通义万相视频生成提示词（中文为主，专业术语用英文，不超过800字符）\n"
            "  格式：主体描述 + 场景描述 + 运动描述(核心) + 运镜 + 风格/氛围\n"
            "  运动描述是关键：明确描述主体如何运动、姿态变化、环境动态（如'缓缓转身'、'裙摆随风飘动'）\n"
            "  运镜词示例：固定镜头、镜头推进、镜头拉远、横移、环绕运镜、航拍、Tracking Shot\n"
            "  景别词示例：特写、近景、中景、全景、广角\n"
            "  光线/氛围词示例：柔光、侧光、暖色调、冷色调、黄金时刻、高对比度、胶片质感\n"
            "  速度词示例：慢动作、延时拍摄、正常速度\n"
            "- video_duration: 该镜头视频时长（秒，默认3.0）\n\n"
            "**重要：image_prompt 和 video_prompt 中必须包含具体的人物外貌描述（年龄、种族特征、衣着），"
            "确保与脚本人物设定一致。**\n\n"
            f"{duration_hint}"
            "请确保 JSON 格式正确，直接返回数组，不要包裹在其他结构中。\n\n"
            f"脚本标题：{script.title}\n"
            f"主题：{script.theme or '未指定'}\n"
            f"叙事类型：{script.narrative_type or '未指定'}\n\n"
            f"{scene_context}"
            f"脚本正文：\n{display_content}"
            f"{visual_reference}"
        )

        request = AIRequest(
            prompt=prompt,
            service_type=ServiceType.TEXT_GENERATION,
            params={"temperature": 0.7, "max_tokens": 4096},
        )

        response = await adapter.generate(request)
        if not response.success:
            logger.warning(f"AI shot generation failed: {response.error}")
            return []

        text = response.data.get("text", "") if response.data else ""
        shot_data_list = self._parse_shots_json(text)
        if not shot_data_list:
            logger.warning("Failed to parse shot data from AI response")
            return []

        shots: list[Shot] = []
        for i, sd in enumerate(shot_data_list, start=1):
            shot = Shot(
                storyboard_id=storyboard.id,
                shot_number=i,
                act_name=sd.get("act_name"),
                time_range=sd.get("time_range"),
                shot_type=sd.get("shot_type"),
                description=sd.get("description", f"Shot {i}"),
                tone=sd.get("tone"),
                mood=sd.get("mood"),
                image_prompt=sd.get("image_prompt"),
                video_prompt=sd.get("video_prompt"),
                video_duration=float(sd.get("video_duration", 3.0)),
            )
            self.db.add(shot)
            shots.append(shot)

        await self.db.flush()
        return shots

    @staticmethod
    def _parse_shots_json(text: str) -> list[dict]:
        """Extract shot list from AI response text."""
        # Try to find a JSON array in the text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start < 0 or end <= start:
            return []
        try:
            parsed = json.loads(text[start:end])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return []
