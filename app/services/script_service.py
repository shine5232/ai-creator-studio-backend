import json
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.models.script import Script
from app.schemas.script import CreateScriptRequest, GenerateScriptRequest, UpdateScriptRequest
from app.utils.logger import logger


def _convert_to_markdown(generated: dict, project_id: int, version: int) -> str:
    """Convert generated script JSON to Markdown format based on template."""
    title = generated.get("title", "未命名脚本")
    theme = generated.get("theme", "")
    narrative_type = generated.get("narrative_type", "")
    duration = generated.get("duration_seconds", 60)
    source_case = generated.get("source_case_id")

    # Get reference case info
    ref_info = ""
    if source_case:
        ref_info = f"\n> 基于 Case {source_case} 爆款逻辑创作"

    # Build character profiles section
    char_profiles = generated.get("character_profiles", [])
    chars_md = ""
    for char in char_profiles:
        role = char.get("role_name", "角色")
        chars_md += f"""
### 角色：{role}

- **年龄**：{char.get("age", "")}
- **性别**：{char.get("gender", "")}
- **国籍/种族**：{char.get("race_ethnicity", "")} ⭐ 必填，必须与原视频保持一致
- **肤色**：{char.get("skin_color", "")} ⭐ 必填，必须与原视频保持一致
- **眼睛**：{char.get("eyes", "")}
- **发型**：{char.get("hair", "")}
- **面部特征**：{char.get("facial_features", "")} ⭐ 必填
- **体型**：{char.get("body_type", "")}
- **特殊标记**：{char.get("special_marks", "")}
- **性格特点**：{char.get("personality", "")}
- **穿着**：
"""
        for phase in char.get("clothing_phases", []):
            chars_md += f'  - {phase.get("phase", "")}：{phase.get("description", "")}\n'

    # Build storyboard section
    acts = generated.get("acts", [])
    storyboard_md = ""
    for act in acts:
        act_num = act.get("act_number", 1)
        act_name = act.get("act_name", f"第{act_num}幕")
        time_range = act.get("time_range", "")
        storyboard_md += f"""
### 第{act_num}幕：{act_name}（{time_range}）

"""
        shots = act.get("shots", [])
        for shot in shots:
            shot_num = shot.get("shot_number", 1)
            shot_time = shot.get("time_range", "")
            shot_type = shot.get("shot_type", "")
            location = shot.get("location", "")
            characters = shot.get("characters", "")
            environment = shot.get("environment", "")
            event = shot.get("event", "")
            dialog = shot.get("dialog", "")
            tone = shot.get("tone", "")
            mood = shot.get("mood", "")

            storyboard_md += f"""**镜头 {shot_num} | {shot_time} | {location}**
| 项目 | 描述 |
|------|------|
| **镜头** | {shot_type} |
| **人物** | {characters} |
| **环境** | {environment} |
| **事件** | {event} |
"""
            if dialog:
                storyboard_md += f"| **台词** | {dialog} |\n"
            storyboard_md += f"""| **色调** | {tone} |
| **氛围** | {mood} |

"""

    # Build visual design section
    visual = generated.get("visual_design", {})
    visual_md = """
## 🎨 视觉对比设计

### 场景对比
"""
    contrasts = visual.get("contrasts", [])
    if contrasts:
        visual_md += "| 前期场景 | 后期场景 | 象征意义 |\n"
        visual_md += "|----------|----------|----------|\n"
        for c in contrasts:
            visual_md += f"| {c.get('before', '')} | {c.get('after', '')} | {c.get('symbol', '')} |\n"

    color_prog = visual.get("color_progression", "")
    visual_md += f"""
### 色调变化
- **整体色调变化**：{color_prog}

### 视觉符号
"""
    symbols = visual.get("visual_symbols", [])
    if symbols:
        visual_md += "| 符号 | 象征意义 |\n"
        visual_md += "|------|----------|\n"
        for s in symbols:
            visual_md += f"| {s.get('symbol', '')} | {s.get('meaning', '')} |\n"

    # Build viral elements section
    viral = generated.get("viral_elements", [])
    viral_md = """
## ✅ 爆款元素检查

### 话题层
"""
    for v in viral:
        viral_md += f"- ✅ {v}\n"

    # Build title suggestions
    titles = generated.get("title_suggestions", [])
    titles_md = """
## 📝 标题建议

### 推荐标题
"""
    for t in titles:
        if t.get("recommended"):
            titles_md += f"- **{t.get('title', '')}** ⭐ 推荐\n"
        else:
            titles_md += f"- {t.get('title', '')}\n"

    # Content section
    content = generated.get("content", "")

    # Combine all sections
    md = f"""# 🎬 脚本大纲：{title}

{ref_info}
> 主题：{theme}
> 时长：{duration}秒

---

## 📊 创作说明

### 核心要素
- **主题**：{theme}
- **叙事类型**：{narrative_type}
- **时长**：{duration}秒

---

## 🎭 人物设定
{chars_md}
---

## 📝 故事梗概

{content}

---

## 📝 分镜脚本
{storyboard_md}
{visual_md}
{viral_md}
{titles_md}
---

*创作时间：{Path.cwd().name}*
*项目ID：{project_id}*
*脚本版本：v{version}*
"""
    return md


async def _save_script_to_file(project_id: int, version: int, markdown_content: str, title: str) -> str:
    """Save script markdown to project directory."""
    # Create project scripts directory
    scripts_dir = Path(f"data/projects/{project_id}/scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize title for filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = "script"

    # Generate filename
    filename = f"{safe_title}_v{version}.md"
    file_path = scripts_dir / filename

    # Write markdown content
    file_path.write_text(markdown_content, encoding="utf-8")

    logger.info(f"Script saved to: {file_path}")
    return str(file_path)


def _parse_script_json(text: str) -> dict | None:
    """从 AI 返回文本中提取脚本 JSON。支持 markdown 代码块包裹和多层嵌套 JSON。"""
    if not text:
        return None

    # 1. 去掉 markdown 代码块包裹（```json ... ``` 或 ``` ... ```）
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # 去掉开头的 ```json 或 ```
        first_newline = cleaned.find("\n")
        if first_newline >= 0:
            cleaned = cleaned[first_newline + 1:]
        # 去掉结尾的 ```
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()

    # 2. 尝试直接解析整个 cleaned
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "content" in parsed:
            logger.info("Parsed script JSON directly (full text)")
            return parsed
    except json.JSONDecodeError:
        pass

    # 3. 找到第一个 { ，然后用括号匹配法找到对应的 }
    start = cleaned.find("{")
    if start < 0:
        logger.warning(f"No JSON object found in AI response (len={len(text)})")
        return None

    # 用栈匹配括号，正确处理嵌套和字符串内的括号
    depth = 0
    in_string = False
    escape = False
    end = -1
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end <= start:
        logger.warning(f"Could not find matching JSON braces (start={start})")
        return None

    try:
        parsed = json.loads(cleaned[start:end])
        if isinstance(parsed, dict) and "content" in parsed:
            logger.info(f"Parsed script JSON via brace matching (len={end - start})")
            return parsed
        logger.warning(f"JSON parsed but missing 'content' key, keys: {list(parsed.keys())}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode failed at brace-matched region: {e}")
        # 最后手段：截断到最后一个 } 重试
        for fallback_end in range(len(cleaned) - 1, end, -1):
            if cleaned[fallback_end] == '}':
                try:
                    parsed = json.loads(cleaned[start:fallback_end + 1])
                    if isinstance(parsed, dict) and "content" in parsed:
                        logger.info(f"Parsed script JSON via fallback (pos={fallback_end})")
                        return parsed
                except json.JSONDecodeError:
                    continue
        logger.error(f"All JSON parse attempts failed. Text preview: {text[:500]}")

    return None


class ScriptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_scripts(self, project_id: int) -> list[Script]:
        result = await self.db.execute(
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
        return result.scalars().all()

    async def create_script(self, project_id: int, data: CreateScriptRequest) -> Script:
        # 验证 source_case_id 有效性
        if data.source_case_id:
            from app.services.knowledge_service import KnowledgeService
            ks = KnowledgeService(self.db)
            case = await ks.get_case(data.source_case_id)
            if not case or case.analysis_status != "completed":
                raise ValueError(f"参考案例 {data.source_case_id} 不存在或未完成分析")

        # Mark previous scripts as not current
        await self.db.execute(
            update(Script)
            .where(Script.project_id == project_id)
            .values(is_current=False)
        )

        # Get next version number
        result = await self.db.execute(
            select(Script).where(Script.project_id == project_id).order_by(Script.version.desc())
        )
        latest = result.scalar_one_or_none()
        next_version = (latest.version + 1) if latest else 1

        script = Script(
            project_id=project_id,
            title=data.title,
            theme=data.theme,
            sub_theme=data.sub_theme,
            duration_seconds=data.duration_seconds,
            narrative_type=data.narrative_type,
            content=data.content,
            viral_elements=json.dumps(data.viral_elements) if data.viral_elements else None,
            source_case_id=data.source_case_id,
            version=next_version,
            is_current=True,
        )
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        logger.info(f"Script created: {script.id} v{script.version}")
        return script

    async def get_script(self, script_id: int) -> Script | None:
        result = await self.db.execute(select(Script).where(Script.id == script_id))
        return result.scalar_one_or_none()

    async def update_script(self, script_id: int, data: UpdateScriptRequest) -> Script:
        script = await self.get_script(script_id)
        if not script:
            raise ValueError("Script not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "viral_elements" and value is not None:
                value = json.dumps(value)
            setattr(script, field, value)

        await self.db.commit()
        await self.db.refresh(script)
        return script

    async def delete_script(self, script_id: int) -> bool:
        script = await self.get_script(script_id)
        if not script:
            return False
        await self.db.delete(script)
        await self.db.commit()
        return True

    async def check_viral(self, script_id: int) -> dict:
        """Analyze script content for viral elements using GLM."""
        script = await self.get_script(script_id)
        if not script:
            raise ValueError("Script not found")

        providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
        if not providers:
            raise ValueError("No AI provider available for text generation")

        adapter = providers[0]

        # 从知识库加载高频爆款元素作为对比参考
        from app.models.knowledge import KBElement
        kb_hints = ""
        elem_result = await self.db.execute(
            select(KBElement)
            .where(KBElement.element_type == "viral")
            .order_by(KBElement.impact_score.desc())
            .limit(10)
        )
        top_elements = elem_result.scalars().all()
        if top_elements:
            names = [e.name for e in top_elements]
            kb_hints = (
                f"\n\n【知识库高频爆款元素参考】\n{', '.join(names)}\n"
                "请评估脚本是否包含类似元素，并给出建议。"
            )

        prompt = (
            "你是一个专业的短视频病毒传播分析师。请分析以下脚本内容，"
            "从以下维度评估其病毒传播潜力，并以 JSON 格式返回：\n"
            "1. hook_strength (开头吸引力 1-10)\n"
            "2. emotional_triggers (情感触发点列表)\n"
            "3. shareability (分享意愿 1-10)\n"
            "4. trend_alignment (热点契合度 1-10)\n"
            "5. suggested_viral_elements (建议增加的病毒元素)\n"
            "6. overall_score (综合评分 1-100)\n"
            "7. analysis (一段简短的中文分析总结)\n\n"
            f"脚本标题：{script.title}\n"
            f"主题：{script.theme or '未指定'}\n"
            f"脚本内容：\n{script.content}"
            f"{kb_hints}"
        )

        request = AIRequest(
            prompt=prompt,
            service_type=ServiceType.TEXT_GENERATION,
        )

        response = await adapter.generate(request)

        if not response.success:
            raise RuntimeError(f"AI analysis failed: {response.error}")

        # Parse the analysis text
        analysis_text = ""
        if response.data:
            analysis_text = response.data.get("text", response.data.get("content", ""))

        # Try to extract JSON from the response
        analysis_result = {"raw_analysis": analysis_text}
        try:
            # Look for JSON block in the response
            start = analysis_text.find("{")
            end = analysis_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(analysis_text[start:end])
                analysis_result = parsed
        except json.JSONDecodeError:
            pass

        # Update script with viral elements
        script.viral_elements = json.dumps(analysis_result, ensure_ascii=False)
        await self.db.commit()

        logger.info(f"Viral analysis complete for script {script_id}")
        return {"script_id": script_id, "analysis": analysis_result}

    async def generate_script(self, project_id: int, data: GenerateScriptRequest) -> Script:
        """AI 自动生成脚本并入库。"""
        providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
        if not providers:
            raise ValueError("No AI provider available for text generation")
        adapter = providers[0]

        # 1. 知识库参考（可选）
        kb_reference = ""
        ctx = None
        if data.source_case_id:
            from app.services.knowledge_service import KnowledgeService
            ks = KnowledgeService(self.db)
            ctx = await ks.get_reference_context(data.source_case_id)
            if ctx:
                story_part = f"故事梗概: {ctx['story_summary']}\n" if ctx.get("story_summary") else ""
                chars_part = f"人物外貌特征: {ctx['characters_ethnicity']}\n" if ctx.get("characters_ethnicity") else ""
                narrative_part = f"叙事结构: {ctx['narrative_structure']}\n" if ctx.get("narrative_structure") else ""
                emotion_part = f"情感触发点: {ctx['emotion_triggers']}\n" if ctx.get("emotion_triggers") else ""
                contrast_part = f"视觉对比: {ctx['visual_contrast']}\n" if ctx.get("visual_contrast") else ""
                audience_part = f"受众画像: {ctx['audience_profile']}\n" if ctx.get("audience_profile") else ""
                reusable = ctx.get('reusable_elements', {})
                reusable_part = ""
                if isinstance(reusable, dict):
                    if reusable.get("narrative_template"):
                        reusable_part += f"叙事模板: {reusable['narrative_template']}\n"
                    if reusable.get("visual_template"):
                        reusable_part += f"视觉模板: {reusable['visual_template']}\n"

                # Handle viral_elements which may be a dict with layers
                viral_list = ctx.get('viral_elements', [])
                if isinstance(viral_list, dict):
                    viral_str = []
                    for layer, items in viral_list.items():
                        if isinstance(items, list):
                            viral_str.append(f"{layer}: {', '.join(items)}")
                    viral_part = f"爆款元素:\n" + "\n".join(viral_str) + "\n"
                else:
                    viral_part = f"爆款元素: {', '.join(viral_list)}\n"

                kb_reference = (
                    f"\n\n【参考爆款案例】\n"
                    f"标题: {ctx['title']} (点赞率: {ctx['like_rate']})\n"
                    f"主题: {ctx['theme']}\n"
                    f"叙事类型: {ctx['narrative_type']}\n"
                    f"{narrative_part}"
                    f"{story_part}"
                    f"情感曲线: {ctx['emotion_curve']}\n"
                    f"{emotion_part}"
                    f"视觉风格: {ctx['visual_style']}\n"
                    f"{contrast_part}"
                    f"视觉符号: {', '.join(ctx['visual_symbols'])}\n"
                    f"{viral_part}"
                    f"{audience_part}"
                    f"{reusable_part}"
                    f"标题公式: {ctx['title_formula']}\n"
                    f"{chars_part}"
                    f"请严格参考以上案例的风格、人物外貌、视觉风格和结构来创作。"
                )

        # 2. 高频爆款元素（自动注入）
        from app.models.knowledge import KBElement
        kb_hints = ""
        elem_result = await self.db.execute(
            select(KBElement)
            .where(KBElement.element_type == "viral")
            .order_by(KBElement.impact_score.desc())
            .limit(10)
        )
        top_elements = elem_result.scalars().all()
        if top_elements:
            kb_hints = f"\n\n【高频爆款元素参考】{', '.join(e.name for e in top_elements)}\n请适当融入以上元素。"

        # 3. 构建时长指引
        target_words = (data.duration_seconds or 60) * 3
        duration_guide = f"目标时长 {data.duration_seconds or 60} 秒，脚本正文约 {target_words} 字。"

        # 4. 额外要求
        custom = f"\n\n【额外要求】{data.custom_prompt}" if data.custom_prompt else ""

        # 5. 构建富结构 prompt
        prompt = (
            "你是一个专业的短视频脚本作家兼导演。请根据以下要求创作一个**完整的分镜级别脚本**，"
            "包含详细的人物设定、分幕分镜头、视觉对比设计和爆款元素分析。\n\n"
            f"标题方向: {data.title}\n"
            f"主题: {data.theme or '不限'}\n"
            f"子主题: {data.sub_theme or '不限'}\n"
            f"叙事类型: {data.narrative_type or '不限'}\n"
            f"{duration_guide}"
            f"{kb_reference}{kb_hints}{custom}\n\n"

            "## 输出格式（严格 JSON）\n\n"

            "```\n"
            "{\n"
            '  "title": "脚本标题",\n'
            '  "theme": "主题",\n'
            '  "narrative_type": "叙事类型",\n'
            '  "content": "完整详细的叙事短文（600-1000字），见下方\"脚本正文规则\"",\n\n'

            '  "character_profiles": [\n'
            '    {\n'
            '      "role_name": "角色名（必须与标题主题一致，如标题含\"父爱\"则为父亲）",\n'
            '      "age": 45,\n'
            '      "gender": "女性",\n'
            '      "race_ethnicity": "国籍/种族（必须与参考案例保持一致）",\n'
            '      "skin_color": "肤色描述（如：微黑皮肤，粗糙质感）",\n'
            '      "eyes": "眼睛描述（颜色、眼神特点）",\n'
            '      "hair": "发型发质描述",\n'
            '      "facial_features": "面部特征（鼻梁、眼窝、脸型等）",\n'
            '      "body_type": "体型描述（身高、胖瘦、姿态）",\n'
            '      "special_marks": "特殊标记（疤痕、老茧等）",\n'
            '      "personality": "性格特点",\n'
            '      "clothing_phases": [\n'
            '        {"phase": "前期", "description": "前期穿着描述"},\n'
            '        {"phase": "中期", "description": "中期穿着描述"},\n'
            '        {"phase": "后期", "description": "后期穿着描述"}\n'
            '      ]\n'
            '    }\n'
            '  ],\n\n'

            '  "acts": [\n'
            '    {\n'
            '      "act_number": 1,\n'
            '      "act_name": "幕名（如：橱窗向往）",\n'
            '      "time_range": "0-15s",\n'
            '      "shots": [\n'
            '        {\n'
            '          "shot_number": 1,\n'
            '          "time_range": "0-3s",\n'
            '          "shot_type": "景别（特写/中景/远景/跟拍等）",\n'
            '          "location": "拍摄地点",\n'
            '          "characters": "人物动作与表情（含年龄、外貌细节）",\n'
            '          "environment": "环境描写（时代背景、具体地点、光线、细节）",\n'
            '          "event": "发生的事件/动作",\n'
            '          "dialog": "台词或旁白（如有）",\n'
            '          "tone": "画面色调（如：暗黄色，整体偏暗）",\n'
            '          "mood": "情感氛围关键词"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ],\n\n'

            '  "visual_design": {\n'
            '    "color_progression": "整体色调变化（如：暗沉→明亮→温馨→高雅）",\n'
            '    "contrasts": [\n'
            '      {"before": "前期场景", "after": "后期场景", "symbol": "象征意义"}\n'
            '    ],\n'
            '    "visual_symbols": [\n'
            '      {"symbol": "视觉符号", "meaning": "象征意义"}\n'
            '    ]\n'
            '  },\n\n'

            '  "title_suggestions": [\n'
            '    {"title": "标题1", "recommended": true},\n'
            '    {"title": "标题2", "recommended": false}\n'
            '  ],\n\n'

            '  "viral_elements": ["爆款元素1", "爆款元素2"]\n'
            '}\n'
            "```\n\n"

            "## 关键创作规则\n\n"

            "### 核心原则：主题一致性（最重要）\n"
            "1. **角色必须与标题主题严格一致**：标题是\"父爱的力量\"就必须写父亲，标题是\"母爱的力量\"就必须写母亲，绝不能混淆\n"
            "2. **参考案例只参考风格和结构**：参考案例中的人物、种族、视觉风格可以作为参考，但如果参考案例的角色性别/身份与当前标题冲突，必须按标题主题来设定角色\n"
            "3. **故事简洁有力**：短视频脚本不要复杂的多线叙事，要一个核心冲突、一个情感转折、一个直击人心的结局\n\n"

            "### 脚本正文规则（content 字段 — 最重要）\n"
            "content 字段是一篇**完整的叙事短文**，是整个视频故事的详细文字版，要求：\n"
            "1. **字数**：600-1000字，不能少于600字\n"
            "2. **叙事结构**：三段式直击痛点 —\n"
            "   - 开场（前1/3）：用一个强画面快速建立人物和困境，让观众在3秒内产生共情\n"
            "   - 转折（中1/3）：一个关键动作或事件，引爆情感\n"
            "   - 高潮+结尾（后1/3）：情感释放，给观众一个满意或震撼的结局\n"
            "3. **叙事方式**：第三人称全知视角，像写小说一样讲述，包含场景描写、人物心理、动作细节、对话\n"
            "4. **人物描写**：每次人物出场都要描述外貌细节（年龄、肤色、穿着、表情）\n"
            "5. **场景描写**：每个场景都要有具体的环境描写（地点、光线、色调、细节）\n"
            "6. **情感节奏**：不要多个转折，只做一个情感爆发点，但要做得足够深、足够真\n"
            "7. **对话**：关键情节要有对话，对话简短有力，符合人物身份\n"
            "8. **画面感**：每个段落都要有强烈的画面感，读者读完后能在脑海中看到完整的视频画面\n\n"

            "### 人物描写规则\n"
            "1. **角色性别/身份必须与标题主题匹配**（如标题含\"父爱\"则主角是父亲，含\"母爱\"则是母亲）\n"
            "2. **种族/国籍**：如果参考案例有明确种族特征则保持一致，否则根据故事背景自行设定\n"
            "3. **每个字段都必须填写具体描述**，不能留空或写\"同上\"\n"
            "4. clothing_phases 必须包含前期/中期/后期的穿着变化\n"
            "5. 描写级别示例：不能写\"一个男人\"，要写\"一个约50岁的东南亚裔男人，黝黑皮肤，花白短发，穿着褪色的蓝色工装\"\n\n"

            "### 分镜规则\n"
            "1. 脚本分为 3-4 幕（acts），每幕包含 3-5 个镜头（shots），总共 10-20 个镜头\n"
            "2. 每个镜头约3秒，总镜头数 = 目标时长 / 3\n"
            "3. 每个镜头必须包含：景别、地点、人物动作表情、环境细节、事件、色调、氛围\n"
            "4. 人物描写中要带上具体年龄和外貌细节\n"
            "5. 环境描写要具体：不能写\"一间屋子\"，要写\"一间昏暗破旧的出租屋，墙上贴着发黄的报纸\"\n"
            "6. **分镜节奏**：前几镜快速建立情境，中间几镜铺垫，最后几镜集中爆发情感\n\n"

            "### 视觉设计规则\n"
            "1. color_progression 要体现整体色调演变\n"
            "2. contrasts 要包含至少2组前后对比\n"
            "3. visual_symbols 要包含至少3个关键视觉符号及其象征意义\n\n"

            "### 标题规则\n"
            "1. 提供 3 个标题建议\n"
            "2. 推荐标题标 recommended: true\n"
            "3. 标题要包含转折物+行动+情感结果\n\n"

            "直接返回 JSON，不要包裹在 markdown 代码块中。"
        )

        # 6. 调用 AI
        response = await adapter.generate(
            AIRequest(
                prompt=prompt,
                service_type=ServiceType.TEXT_GENERATION,
                params={"temperature": 0.8, "max_tokens": 8192, "timeout": 240},
            )
        )
        if not response.success:
            raise RuntimeError(f"AI script generation failed: {response.error}")

        text = response.data.get("text", "") if response.data else ""
        generated = _parse_script_json(text)
        if not generated:
            raise RuntimeError("Failed to parse AI generated script")

        # 7. 组合 content：可读正文 + 结构化 JSON（供下游分镜解析）
        structured = {
            "character_profiles": generated.get("character_profiles", []),
            "acts": generated.get("acts", []),
            "visual_design": generated.get("visual_design", {}),
            "title_suggestions": generated.get("title_suggestions", []),
        }

        enriched_content = generated["content"]
        structured_block = json.dumps(structured, ensure_ascii=False)
        enriched_content += "\n\n---STRUCTURED_DATA---\n" + structured_block

        # 8. 生成 Markdown 格式脚本并保存到文件
        markdown_content = _convert_to_markdown(generated, project_id, next_version)
        script_path = await _save_script_to_file(
            project_id, next_version, markdown_content, generated.get("title", "script")
        )

        # 8. 入库（复用版本管理逻辑）
        await self.db.execute(
            update(Script).where(Script.project_id == project_id).values(is_current=False)
        )
        result = await self.db.execute(
            select(Script).where(Script.project_id == project_id).order_by(Script.version.desc())
        )
        latest = result.scalar_one_or_none()
        next_version = (latest.version + 1) if latest else 1

        script = Script(
            project_id=project_id,
            title=generated.get("title", data.title),
            theme=generated.get("theme", data.theme),
            sub_theme=data.sub_theme,
            duration_seconds=data.duration_seconds,
            narrative_type=generated.get("narrative_type", data.narrative_type),
            content=enriched_content,
            viral_elements=json.dumps(generated.get("viral_elements"), ensure_ascii=False),
            source_case_id=data.source_case_id,
            script_path=script_path,
            version=next_version,
            is_current=True,
        )
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        logger.info(f"AI generated script: {script.id} v{script.version}")
        return script
