"""诊断后端数据库连接问题"""
import os
from app.config import settings

print("=== Database Configuration ===")
print(f"DATABASE_URL from env: {os.getenv('DATABASE_URL', 'Not set')}")
print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
print(f"Has 'mysql' in URL: {'mysql' in settings.DATABASE_URL.lower()}")
print(f"Has 'sqlite' in URL: {'sqlite' in settings.DATABASE_URL.lower()}")

# 尝试连接数据库并查询
import asyncio
from app.database import async_session_maker
from app.models.knowledge import KBCase
from sqlalchemy import select

async def check_database():
    async with async_session_maker() as db:
        result = await db.execute(select(KBCase))
        cases = result.scalars().all()
        print(f"\n=== Database Content ===")
        print(f"Total KBCase records: {len(cases)}")
        for case in cases:
            print(f"  ID={case.id}, Platform={case.platform}, Status={case.analysis_status}")

asyncio.run(check_database())
