"""为所有缺少 video_prompt 的分镜补充生成图生视频提示词。"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_maker
from app.models.script import Shot, Storyboard, Script
from app.models.character import Character
from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.ai_gateway.providers.glm_adapter import QwenAdapter
from app.utils.logger import logger


async def main():
    # 注册 AI provider（脚本独立运行，不经过 FastAPI lifespan）
    registry.register(QwenAdapter())

    providers = registry.get_providers_for_service(ServiceType.TEXT_GENERATION)
    if not providers:
        print("ERROR: No text generation provider available")
        return
    adapter = providers[0]

    async with async_session_maker() as session:
        # 查找所有 video_prompt 为空的 shots
        result = await session.execute(
            select(Shot)
            .where((Shot.video_prompt == None) | (Shot.video_prompt == ""))  # noqa: E711
            .order_by(Shot.id)
        )
        shots = result.scalars().all()

    if not shots:
        print("没有需要补充 video_prompt 的分镜。")
        return

    print(f"找到 {len(shots)} 个缺少 video_prompt 的分镜，开始生成...")

    # 按 storyboard_id 分组，预加载关联数据
    storyboard_ids = list({s.storyboard_id for s in shots})
    script_map: dict[int, Script] = {}
    char_map: dict[int, list] = {}  # project_id -> characters

    async with async_session_maker() as session:
        for sb_id in storyboard_ids:
            sb = await session.get(Storyboard, sb_id)
            if sb:
                script = await session.get(Script, sb.script_id)
                if script:
                    script_map[sb_id] = script
                    # 加载人物设定
                    if script.project_id not in char_map:
                        cr = await session.execute(
                            select(Character).where(Character.project_id == script.project_id)
                        )
                        chars = cr.scalars().all()
                        if chars:
                            lines = ["以下是脚本中的人物设定：\n"]
                            for c in chars:
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
                            char_map[script.project_id] = "\n".join(lines)

    completed = 0
    total = len(shots)

    for shot in shots:
        script = script_map.get(shot.storyboard_id)
        if not script:
            print(f"  Shot {shot.id}: 跳过（找不到关联脚本）")
            completed += 1
            continue

        # 构建人物设定文本
        char_text = char_map.get(script.project_id, "")
        if not char_text and script.content and "---STRUCTURED_DATA---" in script.content:
            from app.worker.tasks.generation import _build_character_profiles_text
            char_text = _build_character_profiles_text(script.content)

        # 构建视觉风格
        visual_style = ""
        if script.content and "---STRUCTURED_DATA---" in script.content:
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
        prompt = (
            "你是一个专业的AI图生视频提示词工程师。请根据以下分镜信息，生成一条适合万相/Seedance 图生视频模型的提示词。\n\n"
            "## 图生视频提示词要求\n"
            "1. 描述画面中应该发生的动态变化和运动（如人物转头、微风吹动头发、光线变化等）\n"
            "2. 描述镜头运动（如缓慢推进、微微摇晃、固定镜头等）\n"
            "3. 简洁精准，只描述视频中的动态元素，不要重复静态描述\n"
            "4. 中文为主，英文不超过50个词\n"
            "5. 控制在1-3句话以内\n"
            "6. 格式：主体描述 + 场景描述 + 运动描述(核心) + 运镜 + 风格/氛围\n\n"
            "## 关键规则\n"
            "- 只返回提示词文本本身，不要任何解释、前缀、代码块\n\n"
            f"## 脚本标题：{script.title}\n\n"
            f"## 人物设定\n{char_text}\n\n"
            f"## 当前镜头信息\n"
            f"- 幕名：{shot.act_name or '未知'}\n"
            f"- 景别：{shot.shot_type or '未指定'}\n"
            f"- 镜头描述：{shot.description}\n"
            f"- 色调：{shot.tone or '未指定'}\n"
            f"- 氛围：{shot.mood or '未指定'}\n"
        )
        if shot.image_prompt:
            prompt += f"\n## 已有文生图提示词（参考）\n{shot.image_prompt}\n\n"
        prompt += "请生成图生视频提示词："

        try:
            response = await adapter.generate(AIRequest(
                prompt=prompt,
                service_type=ServiceType.TEXT_GENERATION,
                params={"temperature": 0.7, "max_tokens": 512},
            ))

            if response.success and response.data:
                text = response.data.get("text", "").strip()
                # 去除 markdown 代码块
                if text.startswith("```"):
                    first_nl = text.find("\n")
                    if first_nl >= 0:
                        text = text[first_nl + 1:]
                    if text.rstrip().endswith("```"):
                        text = text.rstrip()[:-3].rstrip()

                async with async_session_maker() as session:
                    db_shot = await session.get(Shot, shot.id)
                    if db_shot:
                        db_shot.video_prompt = text
                        await session.commit()

                completed += 1
                print(f"  [{completed}/{total}] Shot {shot.id} (#{shot.shot_number}): video_prompt 已生成 ({len(text)}字)")
            else:
                completed += 1
                print(f"  [{completed}/{total}] Shot {shot.id}: AI 生成失败 - {response.error}")

        except Exception as e:
            completed += 1
            print(f"  [{completed}/{total}] Shot {shot.id}: 异常 - {e}")

    print(f"\n完成！共处理 {total} 个分镜。")


if __name__ == "__main__":
    asyncio.run(main())
