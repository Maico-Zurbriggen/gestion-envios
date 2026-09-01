
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SucursalModel


class RepositorioSucursales:
    """Implementación de acceso a datos para la entidad Sucursal con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar_todas(self) -> list[SucursalModel]:
        """Catálogo completo para `GET /sucursales`, ordenado por nombre
        para que el selector del frontend salga ya ordenado."""
        stmt = select(SucursalModel).order_by(SucursalModel.nombre)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def obtener_por_id(self, id: int) -> SucursalModel | None:
        """Valida el `sucursal_destino_id` de un envío con retiro en
        sucursal (HU03) antes de persistirlo."""
        stmt = select(SucursalModel).where(SucursalModel.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
