import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.base import AIRequest, ServiceType
from app.ai_gateway.registry import registry
from app.models.character import Character, CharacterPeriod
from app.schemas.character import CreateCharacterRequest, UpdateCharacterRequest
from app.utils.logger import logger


class CharacterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_characters(self, project_id: int) -> list[Character]:
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        return result.scalars().all()

    async def create_character(self, project_id: int, data: CreateCharacterRequest) -> Character:
        character = Character(
            project_id=project_id,
            **data.model_dump(),
        )
        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)
        logger.info(f"Character created: {character.id} - {character.name}")
        return character

    async def get_character(self, character_id: int) -> Character | None:
        result = await self.db.execute(
            select(Character).where(Character.id == character_id)
        )
        return result.scalar_one_or_none()

    async def update_character(self, character_id: int, data: UpdateCharacterRequest) -> Character:
        character = await self.get_character(character_id)
        if not character:
            raise ValueError("Character not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(character, field, value)

        await self.db.commit()
        await self.db.refresh(character)
        return character

    async def delete_character(self, character_id: int) -> bool:
        character = await self.get_character(character_id)
        if not character:
            return False
        await self.db.delete(character)
        await self.db.commit()
        return True

    async def generate_prompt_only(self, character_id: int, aspect_ratio: str = "9:16") -> dict:
        """Generate and save reference prompt from character attributes (no image)."""
        character = await self.get_character(character_id)
        if not character:
            raise ValueError("Character not found")

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

        # 根据宽高比添加构图描述
        if aspect_ratio == "9:16":
            prompt_cn += "，竖屏构图，全身或半身肖像，高质量人物肖像，面部细节丰富，电影级光影"
        elif aspect_ratio == "16:9":
            prompt_cn += "，横屏构图，全身或环境肖像，高质量人物肖像，面部细节丰富，电影级光影"
        else:
            prompt_cn += "，高质量人物肖像，面部细节丰富，电影级光影"

        character.reference_prompt_cn = prompt_cn
        await self.db.commit()
        await self.db.refresh(character)

        logger.info(f"Generated prompt for character {character_id}")
        return {
            "character_id": character_id,
            "reference_prompt_cn": prompt_cn,
        }

    async def generate_reference_image(
        self, character_id: int, provider: str | None = None, aspect_ratio: str = "9:16",
        user_id: int | None = None,
    ) -> dict:
        """Generate character reference image using AI. Returns result info."""
        character = await self.get_character(character_id)
        if not character:
            raise ValueError("Character not found")

        # Resolve user config overrides
        overrides = {}
        adapter_config = {}
        if user_id:
            from app.worker.tasks.generation import _resolve_overrides
            from app.worker.db import get_sync_session
            with get_sync_session() as session:
                overrides = _resolve_overrides(session, user_id, "text_to_image")
            resolved_provider = provider or overrides.pop("override_provider", None)
            resolved_model = overrides.pop("override_model", None)
            adapter_config = overrides.pop("_adapter_config", {})
        else:
            resolved_provider = provider
            resolved_model = None

        adapter = registry.get_provider(resolved_provider) if resolved_provider else None
        if not adapter:
            providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
            if providers:
                adapter = providers[0]
            else:
                raise ValueError("No AI provider found for image generation")

        # Build Chinese prompt from character attributes
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
        prompt_cn += "，高质量人物肖像，面部细节丰富，电影级光影"

        # Use reference_prompt_cn if already set, otherwise use auto-generated
        prompt = character.reference_prompt_cn or prompt_cn

        # Map aspect_ratio to size
        size_map = {"9:16": "1088x1920", "16:9": "1920x1088", "1:1": "1440x1440"}
        size = size_map.get(aspect_ratio, "1088x1920")

        request = AIRequest(
            prompt=prompt,
            service_type=ServiceType.TEXT_TO_IMAGE,
            model=resolved_model,
            params={"size": size, "adapter_config": adapter_config},
            **overrides,
        )

        response = await adapter.generate(request)

        if not response.success:
            raise RuntimeError(f"Image generation failed: {response.error}")

        upload_dir = __import__("pathlib").Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Async adapter: poll for result
        if response.task_id and hasattr(adapter, 'check_task'):
            import asyncio
            max_wait = 300
            interval = 5
            elapsed = 0
            while elapsed < max_wait:
                await asyncio.sleep(interval)
                elapsed += interval
                poll = await adapter.check_task(response.task_id, request=request)
                if poll.success and poll.data:
                    status = poll.data.get("status", "").lower()
                    if status in ("completed", "succeeded"):
                        image_url = poll.data.get("image_url") or poll.data.get("url")
                        if image_url:
                            import httpx
                            img_resp = httpx.get(image_url, timeout=60)
                            filename = f"char_{character_id}_{int(time.time())}.png"
                            filepath = upload_dir / filename
                            filepath.write_bytes(img_resp.content)
                            character.reference_image_path = str(filepath)
                            await self.db.commit()
                            return {"character_id": character_id, "reference_image_path": str(filepath), "status": "completed"}
                        break
                    elif status == "failed":
                        raise RuntimeError("Async image generation task failed")
                elif not poll.success:
                    raise RuntimeError(f"Image poll failed: {poll.error}")
            raise RuntimeError("Image generation timed out")

        # Save the generated image (sync adapter)
        if response.data:
            if "url" in response.data or "image_url" in response.data:
                import httpx
                img_url = response.data.get("url") or response.data.get("image_url")
                img_resp = httpx.get(img_url, timeout=60)
                filename = f"char_{character_id}_{int(time.time())}.png"
                filepath = upload_dir / filename
                filepath.write_bytes(img_resp.content)
                character.reference_image_path = str(filepath)
            elif "base64" in response.data or "image_b64" in response.data:
                import base64
                b64_data = response.data.get("base64") or response.data.get("image_b64")
                filename = f"char_{character_id}_{int(time.time())}.png"
                filepath = upload_dir / filename
                filepath.write_bytes(base64.b64decode(b64_data))
                character.reference_image_path = str(filepath)
            elif "local_path" in response.data:
                character.reference_image_path = response.data["local_path"]

            # Store prompts
            character.reference_prompt_cn = prompt_cn
            await self.db.commit()

        logger.info(f"Reference image generated for character {character_id}")
        return {
            "character_id": character_id,
            "status": "completed",
            "image_path": character.reference_image_path,
        }
