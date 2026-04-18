from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.utils.logger import logger


class AssetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_assets(self, project_id: int, asset_type: str | None = None) -> list[Asset]:
        query = select(Asset).where(Asset.project_id == project_id)
        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
        query = query.order_by(Asset.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_asset(self, asset_id: int) -> Asset | None:
        result = await self.db.execute(select(Asset).where(Asset.id == asset_id))
        return result.scalar_one_or_none()

    async def create_asset(
        self,
        project_id: int,
        file_path: str,
        file_name: str,
        asset_type: str,
        category: str | None = None,
        shot_id: int | None = None,
        **kwargs,
    ) -> Asset:
        path = Path(file_path)
        file_size = path.stat().st_size if path.exists() else None

        asset = Asset(
            project_id=project_id,
            asset_type=asset_type,
            category=category,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            shot_id=shot_id,
            **kwargs,
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        logger.info(f"Asset created: {asset.id} - {file_name}")
        return asset

    async def delete_asset(self, asset_id: int) -> bool:
        asset = await self.get_asset(asset_id)
        if not asset:
            return False

        # Delete file from disk
        path = Path(asset.file_path)
        if path.exists():
            path.unlink()

        await self.db.delete(asset)
        await self.db.commit()
        return True
