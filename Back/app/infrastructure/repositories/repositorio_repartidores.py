import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.application.interfaces.repositorio_repartidores import IRepositorioRepartidores
from app.domain.constants.roles import RolEnum
from app.domain.rules.recorrido_rules import ESTADOS_RECORRIDO_ACTIVOS
from app.infrastructure.db.models import RecorridoModel, RepartidorModel, RolModel, UsuarioModel


class RepositorioRepartidores(IRepositorioRepartidores):
    """Acceso a datos de los repartidores y sus perfiles con SQLAlchemy (soporte de HU10)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar(
        self,
        sucursal_id: int | None = None,
        tipo_reparto: str | None = None,
        activo: bool | None = None,
    ) -> list[UsuarioModel]:
        stmt = (
            select(UsuarioModel)
            .join(RolModel, UsuarioModel.rol_id == RolModel.id)
            .options(selectinload(UsuarioModel.repartidor).joinedload(RepartidorModel.sucursal_base))
            .where(RolModel.nombre == RolEnum.REPARTIDOR.value)
        )

        if sucursal_id is not None or tipo_reparto is not None or activo is not None:
            stmt = stmt.join(RepartidorModel, RepartidorModel.usuario_id == UsuarioModel.id)
            if sucursal_id is not None:
                stmt = stmt.where(RepartidorModel.sucursal_base_id == sucursal_id)
            if tipo_reparto is not None:
                stmt = stmt.where(RepartidorModel.tipo_reparto == tipo_reparto)
            if activo is not None:
                stmt = stmt.where(RepartidorModel.activo.is_(activo))

        stmt = stmt.order_by(UsuarioModel.nombre, UsuarioModel.id)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def obtener_usuario(self, usuario_id: uuid.UUID) -> UsuarioModel | None:
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.repartidor).joinedload(RepartidorModel.sucursal_base))
            .where(UsuarioModel.id == usuario_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def guardar_perfil(self, perfil: RepartidorModel) -> RepartidorModel:
        self.db.add(perfil)
        await self.db.commit()
        stmt = (
            select(RepartidorModel)
            .options(joinedload(RepartidorModel.sucursal_base))
            .where(RepartidorModel.usuario_id == perfil.usuario_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one()

    async def tiene_recorridos_activos(self, usuario_id: uuid.UUID) -> bool:
        stmt = select(
            exists().where(
                RecorridoModel.repartidor_id == usuario_id,
                RecorridoModel.estado.in_(ESTADOS_RECORRIDO_ACTIVOS),
            )
        )
        return bool((await self.db.execute(stmt)).scalar())
