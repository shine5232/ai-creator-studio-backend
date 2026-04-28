"""Resolve user AI config to API credentials for generation tasks."""

import json
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.ai_gateway.key_manager import decrypt_key, _get_fernet
from app.config import settings
from app.models.user_ai_config import UserAIConfig
from app.utils.logger import logger


@dataclass
class ResolvedCredentials:
    api_key: str | None = None
    base_url: str | None = None
    provider: str | None = None
    model_id: str | None = None
    extra_config: dict | None = None


# Provider-specific default base URLs and env key mappings
_PROVIDER_DEFAULTS = {
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "env_key": "DOUBAO_API_KEY",
    },
    "wanx": {
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "env_key": "WANX_API_KEY",
    },
    "seedance": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3/contents/generations",
        "env_key": "SEEDANCE_API_KEY",
    },
    "nano_banana": {
        "base_url": "",
        "env_key": "GEMINI_API_KEY",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
    },
    "grok": {
        "base_url": "https://api.apimart.ai/v1",
        "env_key": "GROK_API_KEY",
    },
    "apimart": {
        "base_url": "https://api.apimart.ai/v1",
        "env_key": "GROK_API_KEY",
    },
    "generic": {
        "base_url": "",
        "env_key": "",
    },
}


def resolve_user_config(
    session: Session, user_id: int, service_type: str
) -> ResolvedCredentials | None:
    """Resolve user config for a given service type using a sync DB session.

    Priority: user's default config → first enabled user config → None (use system)
    """
    # Try user's default config
    result = session.execute(
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

    if not config:
        # Fallback: first enabled config
        result = session.execute(
            select(UserAIConfig).where(
                and_(
                    UserAIConfig.user_id == user_id,
                    UserAIConfig.service_type == service_type,
                    UserAIConfig.is_enabled == True,
                )
            ).limit(1)
        )
        config = result.scalar_one_or_none()

    if not config:
        return None

    # Decrypt API key
    api_key = None
    if config.encrypted_api_key:
        try:
            api_key = decrypt_key(config.encrypted_api_key)
        except Exception as e:
            logger.error(f"Failed to decrypt API key for config {config.id}: {e}")

    # If no user key, try system env
    if not api_key:
        provider_defaults = _PROVIDER_DEFAULTS.get(config.provider, {})
        env_key_name = provider_defaults.get("env_key", "")
        api_key = getattr(settings, env_key_name, "") or None

    # Base URL
    base_url = config.api_base_url
    if not base_url:
        provider_defaults = _PROVIDER_DEFAULTS.get(config.provider, {})
        base_url = provider_defaults.get("base_url", "")

    # Parse extra_config JSON
    extra_config = None
    if config.extra_config:
        try:
            extra_config = json.loads(config.extra_config) if isinstance(config.extra_config, str) else config.extra_config
        except (json.JSONDecodeError, TypeError):
            extra_config = None

    logger.info(
        f"Resolved user {user_id} config for {service_type}: "
        f"provider={config.provider}, model={config.model_id}"
    )

    return ResolvedCredentials(
        api_key=api_key,
        base_url=base_url or None,
        provider=config.provider,
        model_id=config.model_id,
        extra_config=extra_config,
    )
