"""Persistencia del control de descarga en la sucursal de destino."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.application.interfaces.repositorio_descargas import IRepositorioDescargas
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    ControlDescargaModel,
    EnvioModel,
    LecturaDescargaModel,
    PaqueteModel,
    RecorridoModel,
    RecorridoPaqueteModel,
    RepartidorModel,
    SucursalModel,
)


class RepositorioDescargas(IRepositorioDescargas):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _select_control(self):
        return select(ControlDescargaModel).options(
            joinedload(ControlDescargaModel.recorrido).joinedload(RecorridoModel.repartidor).joinedload(RepartidorModel.usuario),
            joinedload(ControlDescargaModel.recorrido).joinedload(RecorridoModel.sucursal_origen),
            joinedload(ControlDescargaModel.sucursal),
            joinedload(ControlDescargaModel.iniciado_por),
            joinedload(ControlDescargaModel.cerrado_por),
            selectinload(ControlDescargaModel.lecturas).joinedload(LecturaDescargaModel.usuario),
        )

    async def recorridos_desde(self, desde: date, estados: tuple[str, ...]) -> list[Any]:
        stmt = (
            select(RecorridoModel)
            .where(
                RecorridoModel.fecha >= desde,
                RecorridoModel.estado.in_(estados),
            )
            .options(
                joinedload(RecorridoModel.repartidor).joinedload(RepartidorModel.usuario),
                joinedload(RecorridoModel.sucursal_origen),
            )
            .order_by(RecorridoModel.fecha.desc(), RecorridoModel.created_at.desc())
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def controles_de_sucursal(
        self, sucursal_id: int, recorrido_ids: list[uuid.UUID], tipo: str
    ) -> dict[uuid.UUID, Any]:
        if not recorrido_ids:
            return {}
        stmt = self._select_control().where(
            ControlDescargaModel.sucursal_id == sucursal_id,
            ControlDescargaModel.recorrido_id.in_(recorrido_ids),
            ControlDescargaModel.tipo == tipo,
        )
        return {c.recorrido_id: c for c in (await self.db.execute(stmt)).unique().scalars().all()}

    async def obtener_control(self, id: uuid.UUID) -> Any | None:
        stmt = self._select_control().where(ControlDescargaModel.id == id).execution_options(populate_existing=True)
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def obtener_control_por(self, recorrido_id: uuid.UUID, sucursal_id: int, tipo: str) -> Any | None:
        stmt = self._select_control().where(
            ControlDescargaModel.recorrido_id == recorrido_id,
            ControlDescargaModel.sucursal_id == sucursal_id,
            ControlDescargaModel.tipo == tipo,
        )
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def obtener_recorrido(self, id: uuid.UUID) -> Any | None:
        stmt = (
            select(RecorridoModel)
            .where(RecorridoModel.id == id)
            .options(
                selectinload(RecorridoModel.paquetes)
                .joinedload(RecorridoPaqueteModel.paquete)
                .joinedload(PaqueteModel.envio)
                .joinedload(EnvioModel.sucursal_destino)
            )
        )
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def obtener_sucursal(self, id: int) -> Any | None:
        return await self.db.get(SucursalModel, id)

    async def paquete_por_numero(self, numero: str) -> Any | None:
        stmt = (
            select(PaqueteModel)
            .where(PaqueteModel.numero_paquete == numero)
            .options(joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino))
        )
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def tiene_alerta_abierta(self, paquete_id: uuid.UUID, motivo: str) -> bool:
        stmt = select(AlertaRecorridoModel.id).where(
            AlertaRecorridoModel.paquete_id == paquete_id,
            AlertaRecorridoModel.motivo == motivo,
            AlertaRecorridoModel.resuelta.is_(False),
        )
        return (await self.db.execute(stmt.limit(1))).first() is not None

    async def agregar(self, entidad: Any) -> None:
        self.db.add(entidad)

    async def confirmar(self) -> None:
        await self.db.commit()
