from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.infrastructure.db.models import EnvioModel, PaqueteModel


class RepositorioEnvios:
    """Implementación de acceso a datos para las entidades Envío y Paquete con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, envio: EnvioModel) -> EnvioModel:
        self.db.add(envio)
        await self.db.commit()
        # Recargar con relaciones de sucursal y paquetes
        return await self._obtener_completo_por_id(envio.id)  # type: ignore

    async def obtener_por_token(self, token: str) -> EnvioModel | None:
        stmt = (
            select(EnvioModel)
            .options(joinedload(EnvioModel.sucursal_destino), selectinload(EnvioModel.paquetes))
            .where(EnvioModel.token_seguimiento == token)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def existe_token(self, token: str) -> bool:
        stmt = select(exists().where(EnvioModel.token_seguimiento == token))
        return bool((await self.db.execute(stmt)).scalar())

    async def existe_numero_paquete(self, numero_paquete: str) -> bool:
        stmt = select(exists().where(PaqueteModel.numero_paquete == numero_paquete))
        return bool((await self.db.execute(stmt)).scalar())

    async def _obtener_completo_por_id(self, id: UUID) -> EnvioModel | None:
        stmt = (
            select(EnvioModel)
            .options(joinedload(EnvioModel.sucursal_destino), selectinload(EnvioModel.paquetes))
            .where(EnvioModel.id == id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()
