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

    async def generate_reference_image(self, character_id: int, provider: str | None = None) -> dict:
        """Generate character reference image using AI. Returns result info."""
        character = await self.get_character(character_id)
        if not character:
            raise ValueError("Character not found")

        adapter = registry.get_provider(provider) if provider else None
        if not adapter:
            providers = registry.get_providers_for_service(ServiceType.TEXT_TO_IMAGE)
            if providers:
                adapter = providers[0]
            else:
                raise ValueError("No AI provider found for image generation")

        # Build prompt from character attributes
        prompt_parts = [f"Character portrait of {character.name}"]
        if character.gender:
            prompt_parts.append(character.gender)
        if character.age:
            prompt_parts.append(f"age {character.age}")
        if character.appearance:
            prompt_parts.append(character.appearance)
        if character.clothing:
            prompt_parts.append(f"wearing {character.clothing}")
        if character.ethnic_features:
            prompt_parts.append(character.ethnic_features)
        if character.skin_tone:
            prompt_parts.append(f"{character.skin_tone} skin")

        prompt = ", ".join(prompt_parts)
        prompt += ", high quality portrait, detailed face, cinematic lighting"

        request = AIRequest(
            prompt=prompt,
            service_type=ServiceType.TEXT_TO_IMAGE,
        )

        response = await adapter.generate(request)

        if not response.success:
            raise RuntimeError(f"Image generation failed: {response.error}")

        # Save the generated image
        if response.data:
            upload_dir = __import__("pathlib").Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)

            if "url" in response.data:
                import httpx
                img_url = response.data["url"]
                img_resp = httpx.get(img_url, timeout=60)
                filename = f"char_{character_id}_{int(time.time())}.png"
                filepath = upload_dir / filename
                filepath.write_bytes(img_resp.content)
                character.reference_image_path = str(filepath)
            elif "base64" in response.data:
                import base64
                filename = f"char_{character_id}_{int(time.time())}.png"
                filepath = upload_dir / filename
                filepath.write_bytes(base64.b64decode(response.data["base64"]))
                character.reference_image_path = str(filepath)
            elif "local_path" in response.data:
                character.reference_image_path = response.data["local_path"]

            # Store the prompt used
            character.reference_prompt_en = prompt
            await self.db.commit()

        logger.info(f"Reference image generated for character {character_id}")
        return {
            "character_id": character_id,
            "status": "completed",
            "image_path": character.reference_image_path,
        }
