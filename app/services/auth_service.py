from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserQuota
from app.schemas.auth import RegisterRequest, UpdateUserRequest
from app.utils.logger import logger


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> User:
        # Check existing
        existing = await self.db.execute(
            select(User).where(
                (User.username == data.username) | (User.email == data.email)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Username or email already exists")

        from app.utils.security import hash_password

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Create default quotas
        for quota_type in ["image_generation", "video_generation", "script_generation", "publish"]:
            self.db.add(UserQuota(user_id=user.id, quota_type=quota_type))
        await self.db.commit()

        logger.info(f"User registered: {user.username}")
        return user

    async def authenticate(self, username: str, password: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        from app.utils.security import verify_password

        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_user(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user(self, user_id: int, data: UpdateUserRequest) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("User not found")

        if data.display_name is not None:
            user.display_name = data.display_name
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("User not found")

        from app.utils.security import verify_password, hash_password

        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Old password incorrect")

        user.hashed_password = hash_password(new_password)
        await self.db.commit()
        return True
