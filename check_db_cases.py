"""检查数据库中的所有案例"""
import asyncio

from app.database import async_session_maker
from app.models.knowledge import KBCase
from sqlalchemy import select


async def list_all_cases():
    async with async_session_maker() as db:
        result = await db.execute(select(KBCase).order_by(KBCase.id))
        cases = result.scalars().all()

        print(f"Total cases: {len(cases)}")
        for case in cases:
            print(f"ID={case.id}, Platform={case.platform}, Status={case.analysis_status}, HasPath={bool(case.analysis_report_path)}")


if __name__ == "__main__":
    asyncio.run(list_all_cases())
