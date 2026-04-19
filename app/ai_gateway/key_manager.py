from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_gateway import APIKey, AIProvider
from app.utils.logger import logger


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        raise ValueError("ENCRYPTION_KEY not configured. Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    return Fernet(key.encode())


def encrypt_key(api_key: str) -> tuple[str, str]:
    f = _get_fernet()
    encrypted = f.encrypt(api_key.encode()).decode()
    hint = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    return encrypted, hint


def decrypt_key(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


async def store_key(db: AsyncSession, provider_name: str, api_key: str):
    encrypted, hint = encrypt_key(api_key)

    # Find provider
    result = await db.execute(
        select(AIProvider).where(AIProvider.name == provider_name)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise ValueError(f"Provider '{provider_name}' not registered")

    # Upsert key
    result = await db.execute(
        select(APIKey).where(APIKey.provider_id == provider.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_key = encrypted
        existing.key_alias = hint
    else:
        db.add(APIKey(
            provider_id=provider.id,
            encrypted_key=encrypted,
            key_alias=hint,
        ))
    await db.commit()
    logger.info(f"API key stored for provider '{provider_name}' (hint: {hint})")


async def get_key(db: AsyncSession, provider_name: str) -> str | None:
    """Get decrypted API key for a provider. Falls back to env config."""
    result = await db.execute(
        select(APIKey)
        .join(AIProvider)
        .where(AIProvider.name == provider_name)
    )
    api_key_record = result.scalar_one_or_none()
    if api_key_record:
        return decrypt_key(api_key_record.encrypted_key)

    # Fallback to environment variable
    env_map = {
        "doubao": settings.DOUBAO_API_KEY,
        "wanx": settings.WANX_API_KEY,
        "seedance": settings.SEEDANCE_API_KEY,
        "nano_banana": settings.GEMINI_API_KEY,
        "qwen": settings.DASHSCOPE_API_KEY,
    }
    return env_map.get(provider_name)


async def get_key_hint(db: AsyncSession, provider_name: str) -> str | None:
    result = await db.execute(
        select(APIKey.key_alias)
        .join(AIProvider)
        .where(AIProvider.name == provider_name)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    # Fallback hint from env
    key = await get_key(db, provider_name)
    if key:
        return f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
    return None
