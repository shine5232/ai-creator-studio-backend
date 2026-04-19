"""直接测试 markdown API 端点"""
import asyncio
from pathlib import Path

from app.database import async_session_maker
from app.models.knowledge import KBCase
from sqlalchemy import select


async def simulate_request():
    """模拟后端 API 处理请求"""
    case_id = 2

    async with async_session_maker() as db:
        # 导入并使用与 API 相同的逻辑
        from sqlalchemy import func

        # 调试：检查数据库中的案例数量
        count_result = await db.execute(select(func.count(KBCase.id)))
        total_count = count_result.scalar()
        print(f"[DEBUG] Total cases in DB: {total_count}")

        # 列出所有案例 ID
        all_ids_result = await db.execute(select(KBCase.id))
        all_ids = all_ids_result.scalars().all()
        print(f"[DEBUG] All case IDs: {list(all_ids)}")

        # 模拟 get_case 调用
        result = await db.execute(select(KBCase).where(KBCase.id == case_id))
        case = result.scalar_one_or_none()

        print(f"[DEBUG] Requested case_id={case_id}, case_found={case is not None}")

        if case:
            print(f"[DEBUG] Case details:")
            print(f"  - platform: {case.platform}")
            print(f"  - status: {case.analysis_status}")
            print(f"  - report_path: {case.analysis_report_path[:50] if case.analysis_report_path else None}...")


if __name__ == "__main__":
    asyncio.run(simulate_request())
