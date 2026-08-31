from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import RolModel


class RepositorioRoles:
    """Implementación de acceso a datos para Roles con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_por_id(self, id: int) -> Optional[RolModel]:
        stmt = select(RolModel).where(RolModel.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_nombre(self, nombre: str) -> Optional[RolModel]:
        stmt = select(RolModel).where(RolModel.nombre == nombre)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

