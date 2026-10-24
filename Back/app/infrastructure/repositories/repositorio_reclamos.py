import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.application.interfaces.repositorio_reclamos import IRepositorioReclamos
from app.infrastructure.db.models import EnvioModel, ReclamoModel


class RepositorioReclamos(IRepositorioReclamos):
    """Acceso a datos de los reclamos con SQLAlchemy (HU07).

    Todas las lecturas precargan envío, paquete y usuario que resolvió: en un
    contexto async un lazy load dispararía `MissingGreenlet` al armar la
    respuesta.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _select_completo(self):
        return select(ReclamoModel).options(
            joinedload(ReclamoModel.envio),
            joinedload(ReclamoModel.paquete),
            joinedload(ReclamoModel.usuario_resolucion),
        )

    async def listar_por_envio(self, envio_id: uuid.UUID) -> list[ReclamoModel]:
        stmt = (
            self._select_completo()
            .where(ReclamoModel.envio_id == envio_id)
            .order_by(ReclamoModel.created_at.desc(), ReclamoModel.id)
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def crear(self, reclamo: ReclamoModel) -> ReclamoModel:
        self.db.add(reclamo)
        await self.db.commit()
        return await self._recargar(reclamo.id)

    async def listar(
        self,
        estado: str | None = None,
        tipo: str | None = None,
        token_seguimiento: str | None = None,
    ) -> list[ReclamoModel]:
        stmt = self._select_completo()
        if estado:
            stmt = stmt.where(ReclamoModel.estado == estado)
        if tipo:
            stmt = stmt.where(ReclamoModel.tipo == tipo)
        if token_seguimiento:
            stmt = stmt.join(EnvioModel, ReclamoModel.envio_id == EnvioModel.id).where(
                EnvioModel.token_seguimiento == token_seguimiento
            )
        stmt = stmt.order_by(ReclamoModel.created_at.desc(), ReclamoModel.id)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def obtener_por_id(self, id: uuid.UUID) -> ReclamoModel | None:
        stmt = self._select_completo().where(ReclamoModel.id == id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def actualizar(self, reclamo: ReclamoModel) -> ReclamoModel:
        await self.db.commit()
        return await self._recargar(reclamo.id)

    async def _recargar(self, id: uuid.UUID) -> ReclamoModel:
        """Vuelve a leer el reclamo: `created_at`/`updated_at` se calculan en la
        base (`func.now()`) y quedan expirados tras el commit."""
        stmt = self._select_completo().where(ReclamoModel.id == id).execution_options(populate_existing=True)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one()
