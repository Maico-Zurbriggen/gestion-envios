"""Consultas de los plazos del circuito: registros sin admitir y retiros vencidos."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.rules.circuito_rules import ESTADOS_ESPERANDO_RETIRO, ESTADOS_PRE_REGISTRO
from app.infrastructure.db.models import EnvioModel, PaqueteModel


class RepositorioPlazos:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def pre_registros_anteriores_a(self, limite: datetime) -> list[Any]:
        stmt = (
            select(PaqueteModel)
            .where(PaqueteModel.estado.in_(ESTADOS_PRE_REGISTRO), PaqueteModel.created_at < limite)
            .options(joinedload(PaqueteModel.envio))
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def retiros_vencidos(self, ahora: datetime) -> list[Any]:
        stmt = (
            select(PaqueteModel)
            .where(
                PaqueteModel.estado.in_(ESTADOS_ESPERANDO_RETIRO),
                PaqueteModel.retiro_hasta.is_not(None),
                PaqueteModel.retiro_hasta < ahora,
                PaqueteModel.en_devolucion.is_(False),
            )
            .options(joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino))
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def agregar(self, entidad: Any) -> None:
        self.db.add(entidad)

    async def confirmar(self) -> None:
        await self.db.commit()
