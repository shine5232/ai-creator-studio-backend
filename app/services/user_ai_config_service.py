import json

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_gateway.key_manager import encrypt_key, decrypt_key
from app.models.user_ai_config import UserAIConfig
from app.schemas.user_ai_config import (
    UserAIConfigCreate,
    UserAIConfigUpdate,
    UserAIConfigResponse,
)
from app.utils.logger import logger


class UserAIConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_configs(
        self, user_id: int, service_type: str | None = None
    ) -> list[UserAIConfig]:
        query = select(UserAIConfig).where(UserAIConfig.user_id == user_id)
        if service_type:
            query = query.where(UserAIConfig.service_type == service_type)
        query = query.order_by(UserAIConfig.is_default.desc(), UserAIConfig.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_config(self, config_id: int, user_id: int) -> UserAIConfig | None:
        result = await self.db.execute(
            select(UserAIConfig).where(
                and_(UserAIConfig.id == config_id, UserAIConfig.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, user_id: int, data: UserAIConfigCreate
    ) -> UserAIConfig:
        # Handle is_default: clear previous default for same service_type
        if data.is_default:
            await self._clear_default(user_id, data.service_type)

        # Encrypt API key if provided
        encrypted_key = None
        key_hint = None
        if data.api_key:
            encrypted_key, key_hint = encrypt_key(data.api_key)

        config = UserAIConfig(
            user_id=user_id,
            config_name=data.config_name,
            provider=data.provider,
            model_id=data.model_id,
            service_type=data.service_type,
            api_base_url=data.api_base_url,
            encrypted_api_key=encrypted_key,
            api_key_hint=key_hint,
            is_enabled=data.is_enabled,
            is_default=data.is_default,
            extra_config=data.extra_config,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        logger.info(f"User {user_id} created AI config '{data.config_name}' (id={config.id})")
        return config

    async def update_config(
        self, config_id: int, user_id: int, data: UserAIConfigUpdate
    ) -> UserAIConfig | None:
        config = await self.get_config(config_id, user_id)
        if not config:
            return None

        # Handle is_default change
        new_service_type = data.service_type or config.service_type
        if data.is_default and not config.is_default:
            await self._clear_default(user_id, new_service_type)

        # Update fields
        if data.config_name is not None:
            config.config_name = data.config_name
        if data.provider is not None:
            config.provider = data.provider
        if data.model_id is not None:
            config.model_id = data.model_id
        if data.service_type is not None:
            config.service_type = data.service_type
        if data.api_base_url is not None:
            config.api_base_url = data.api_base_url
        if data.is_enabled is not None:
            config.is_enabled = data.is_enabled
        if data.is_default is not None:
            config.is_default = data.is_default
        if data.extra_config is not None:
            config.extra_config = data.extra_config

        # Update API key only if provided (non-empty)
        if data.api_key:
            encrypted_key, key_hint = encrypt_key(data.api_key)
            config.encrypted_api_key = encrypted_key
            config.api_key_hint = key_hint

        await self.db.commit()
        await self.db.refresh(config)
        logger.info(f"User {user_id} updated AI config id={config_id}")
        return config

    async def delete_config(self, config_id: int, user_id: int) -> bool:
        config = await self.get_config(config_id, user_id)
        if not config:
            return False
        await self.db.delete(config)
        await self.db.commit()
        logger.info(f"User {user_id} deleted AI config id={config_id}")
        return True

    async def get_default_config(
        self, user_id: int, service_type: str
    ) -> UserAIConfig | None:
        """Get user's default config for a service type."""
        result = await self.db.execute(
            select(UserAIConfig).where(
                and_(
                    UserAIConfig.user_id == user_id,
                    UserAIConfig.service_type == service_type,
                    UserAIConfig.is_default == True,
                    UserAIConfig.is_enabled == True,
                )
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return config

        # Fallback: first enabled config for this type
        result = await self.db.execute(
            select(UserAIConfig).where(
                and_(
                    UserAIConfig.user_id == user_id,
                    UserAIConfig.service_type == service_type,
                    UserAIConfig.is_enabled == True,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none()

    def decrypt_api_key(self, config: UserAIConfig) -> str | None:
        """Decrypt the API key from a config."""
        if config.encrypted_api_key:
            return decrypt_key(config.encrypted_api_key)
        return None

    async def _clear_default(self, user_id: int, service_type: str):
        """Clear is_default for all configs of this user+service_type."""
        result = await self.db.execute(
            select(UserAIConfig).where(
                and_(
                    UserAIConfig.user_id == user_id,
                    UserAIConfig.service_type == service_type,
                    UserAIConfig.is_default == True,
                )
            )
        )
        for config in result.scalars().all():
            config.is_default = False
