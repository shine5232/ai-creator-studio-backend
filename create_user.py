"""Create a default admin user for development."""
import asyncio
from app.database import async_session_maker
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterRequest


async def create_admin_user():
    async with async_session_maker() as db:
        service = AuthService(db)
        try:
            data = RegisterRequest(
                username="admin",
                email="admin@example.com",
                password="admin123"
            )
            user = await service.register(data)
            print("[OK] Admin user created!")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Password: admin123")
        except ValueError as e:
            print(f"[INFO] User already exists or error: {e}")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
