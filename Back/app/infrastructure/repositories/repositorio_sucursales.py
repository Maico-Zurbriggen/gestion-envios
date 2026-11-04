from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SucursalModel, usuario_sucursales


class RepositorioSucursales:
    """Implementación de acceso a datos para la entidad Sucursal con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar_todas(
        self,
        provincia: str | None = None,
        ciudad: str | None = None,
    ) -> list[SucursalModel]:
        """Catálogo para `GET /sucursales`, ordenado por nombre para que el
        selector del frontend salga ya ordenado.

        Los filtros `provincia` y `ciudad` son opcionales (HU09: el usuario que
        espera un paquete filtra por su zona) y comparan sin distinguir
        mayúsculas ni espacios sobrantes. Sin filtros devuelve el catálogo
        completo, igual que antes de HU09.
        """
        stmt = select(SucursalModel)

        if provincia and provincia.strip():
            stmt = stmt.where(func.lower(SucursalModel.provincia) == provincia.strip().lower())
        if ciudad and ciudad.strip():
            stmt = stmt.where(func.lower(SucursalModel.ciudad) == ciudad.strip().lower())

        stmt = stmt.order_by(SucursalModel.nombre)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def obtener_por_id(self, id: int) -> SucursalModel | None:
        """Valida el `sucursal_destino_id` de un envío con retiro en
        sucursal (HU03) y la terminal de recepción de HU06 antes de persistir."""
        stmt = select(SucursalModel).where(SucursalModel.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_nombre(self, nombre: str) -> SucursalModel | None:
        stmt = select(SucursalModel).where(func.lower(SucursalModel.nombre) == nombre.strip().lower())
        return (await self.db.execute(stmt)).scalars().first()

    async def obtener_varias(self, ids: list[int]) -> list[SucursalModel]:
        if not ids:
            return []
        stmt = select(SucursalModel).where(SucursalModel.id.in_(ids)).order_by(SucursalModel.nombre)
        return list((await self.db.execute(stmt)).scalars().all())

    async def contar_usuarios(self) -> dict[int, int]:
        """Cuántos usuarios tienen habilitada cada sucursal."""
        filas = await self.db.execute(
            select(usuario_sucursales.c.sucursal_id, func.count()).group_by(usuario_sucursales.c.sucursal_id)
        )
        return {sucursal: int(cantidad) for sucursal, cantidad in filas.all()}

    def nueva(self, **datos) -> SucursalModel:
        return SucursalModel(**datos)

    async def guardar(self, sucursal: SucursalModel) -> SucursalModel:
        self.db.add(sucursal)
        await self.db.commit()
        await self.db.refresh(sucursal)
        return sucursal
