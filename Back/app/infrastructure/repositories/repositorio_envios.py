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
        """Persiste el envío (con sus paquetes en cascada, vía la relación
        `EnvioModel.paquetes`) y lo vuelve a leer con `sucursal_destino` y
        `paquetes` cargados, listo para armar la respuesta (HU03)."""
        self.db.add(envio)
        await self.db.commit()
        # Recargar con relaciones de sucursal y paquetes
        return await self._obtener_completo_por_id(envio.id)  # type: ignore

    async def obtener_por_token(self, token: str) -> EnvioModel | None:
        """Búsqueda pública de HU04: un token siempre resuelve a un único
        envío con todos sus paquetes, nunca a un paquete individual."""
        stmt = (
            select(EnvioModel)
            .options(joinedload(EnvioModel.sucursal_destino), selectinload(EnvioModel.paquetes))
            .where(EnvioModel.token_seguimiento == token)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def existe_token(self, token: str) -> bool:
        """Usado por `ServicioEnvios._generar_token_unico` para reintentar
        si el candidato generado ya existe (colisión improbable pero posible)."""
        stmt = select(exists().where(EnvioModel.token_seguimiento == token))
        return bool((await self.db.execute(stmt)).scalar())

    async def existe_numero_paquete(self, numero_paquete: str) -> bool:
        """Análogo a `existe_token`, pero para el número de paquete
        (el valor que se codifica en el código de barras de la planilla)."""
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
