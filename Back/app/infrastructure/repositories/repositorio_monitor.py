"""Consultas de solo lectura del monitor de envíos.

Todas las relaciones que se usan al armar la respuesta se precargan: en un
contexto async un lazy load dispara `MissingGreenlet`. La firma de las
entregas no se trae en los listados (es un binario) y se pide aparte.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, defer, joinedload, selectinload

from app.application.interfaces.repositorio_monitor import IRepositorioMonitor
from app.domain.constants.estados_logistica import (
    EstadoNotificacionEnum,
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    ResultadoEventoEntregaEnum,
)
from app.domain.rules.monitor_rules import ESTADOS_RECLAMO_EN_CURSO, GRUPOS_ESTADO
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    EnvioModel,
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    NotificacionEnvioModel,
    PaqueteModel,
    ReclamoModel,
    RecorridoModel,
    RecorridoPaqueteModel,
    RepartidorModel,
    SucursalModel,
)

ORDENES = {
    "movimiento": (PaqueteModel.updated_at.desc(), PaqueteModel.id),
    "recientes": (PaqueteModel.created_at.desc(), PaqueteModel.id),
    "antiguos": (PaqueteModel.created_at.asc(), PaqueteModel.id),
}


def _alerta_abierta():
    """Alerta de recorrido sin resolver (por ejemplo, quedó sin recorrido)."""
    return exists().where(AlertaRecorridoModel.paquete_id == PaqueteModel.id, AlertaRecorridoModel.resuelta.is_(False))


def _reclamo_en_curso():
    """Reclamo en curso sobre el paquete, o sobre todo su envío (sin paquete puntual)."""
    return exists().where(
        ReclamoModel.estado.in_(ESTADOS_RECLAMO_EN_CURSO),
        or_(
            ReclamoModel.paquete_id == PaqueteModel.id,
            and_(ReclamoModel.paquete_id.is_(None), ReclamoModel.envio_id == PaqueteModel.envio_id),
        ),
    )


def _con_problemas():
    return or_(
        PaqueteModel.estado == EstadoPaqueteEnum.ENTREGA_FALLIDA.value,
        _alerta_abierta(),
        _reclamo_en_curso(),
    )


ESPECIALES = {
    "CON_PROBLEMAS": _con_problemas,
    "SIN_RECORRIDO": lambda: _alerta_abierta(),
    "CON_RECLAMO": _reclamo_en_curso,
}


class RepositorioMonitor(IRepositorioMonitor):
    def __init__(self, db: AsyncSession):
        self.db = db
        self._sucursal: int | None = None

    def limitar_a_sucursal(self, sucursal_id: int | None) -> None:
        self._sucursal = sucursal_id

    def _paquetes_de_sucursal(self):
        """Paquetes que pasan por la sucursal: los admitió, están ahí o van a retirarse ahí."""
        envios_destino = select(EnvioModel.id).where(EnvioModel.sucursal_destino_id == self._sucursal)
        return or_(
            PaqueteModel.sucursal_actual_id == self._sucursal,
            PaqueteModel.sucursal_origen_id == self._sucursal,
            PaqueteModel.envio_id.in_(envios_destino),
        )

    def _ids_de_sucursal(self):
        return select(PaqueteModel.id).where(self._paquetes_de_sucursal())

    def _envios_de_sucursal(self):
        return select(PaqueteModel.envio_id).where(self._paquetes_de_sucursal())

    async def _escalar(self, stmt) -> int:
        return int((await self.db.execute(stmt)).scalar() or 0)

    # --- Resumen ------------------------------------------------------------

    async def contar_por_estado(self) -> dict[str, int]:
        stmt = select(PaqueteModel.estado, func.count()).group_by(PaqueteModel.estado)
        if self._sucursal:
            stmt = stmt.where(self._paquetes_de_sucursal())
        filas = await self.db.execute(stmt)
        return {estado: int(cantidad) for estado, cantidad in filas.all()}

    async def contar_devoluciones_en_espera(self) -> int:
        stmt = select(func.count()).select_from(PaqueteModel).where(
            PaqueteModel.en_devolucion.is_(True),
            PaqueteModel.estado.not_in(GRUPOS_ESTADO["DEVOLUCIONES"]),
        )
        if self._sucursal:
            stmt = stmt.where(self._paquetes_de_sucursal())
        return await self._escalar(stmt)

    async def contar_envios(self) -> int:
        stmt = select(func.count()).select_from(EnvioModel)
        if self._sucursal:
            stmt = stmt.where(EnvioModel.id.in_(self._envios_de_sucursal()))
        return await self._escalar(stmt)

    async def contar_paquetes_especiales(self) -> dict[str, int]:
        return {
            clave: await self._escalar(
                select(func.count()).select_from(PaqueteModel).where(
                    condicion(), *([self._paquetes_de_sucursal()] if self._sucursal else [])
                )
            )
            for clave, condicion in ESPECIALES.items()
        }

    async def contar_reclamos_en_curso(self) -> int:
        stmt = select(func.count()).select_from(ReclamoModel).where(ReclamoModel.estado.in_(ESTADOS_RECLAMO_EN_CURSO))
        if self._sucursal:
            stmt = stmt.where(ReclamoModel.envio_id.in_(self._envios_de_sucursal()))
        return await self._escalar(stmt)

    async def contar_notificaciones_fallidas(self) -> int:
        stmt = (
            select(func.count())
            .select_from(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.estado == EstadoNotificacionEnum.FALLIDO.value)
        )
        if self._sucursal:
            stmt = stmt.where(NotificacionEnvioModel.envio_id.in_(self._envios_de_sucursal()))
        return await self._escalar(stmt)

    async def actividad_desde(self, inicio: datetime) -> dict[str, int]:
        eventos = select(func.count()).select_from(EventoEntregaModel).where(EventoEntregaModel.created_at >= inicio)
        registrados = select(func.count()).select_from(PaqueteModel).where(PaqueteModel.created_at >= inicio)
        ingresados = (
            select(func.count())
            .select_from(HistorialEstadoPaqueteModel)
            .where(
                HistorialEstadoPaqueteModel.created_at >= inicio,
                HistorialEstadoPaqueteModel.estado_nuevo == EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value,
            )
        )
        if self._sucursal:
            eventos = eventos.where(EventoEntregaModel.paquete_id.in_(self._ids_de_sucursal()))
            registrados = registrados.where(self._paquetes_de_sucursal())
            ingresados = ingresados.where(HistorialEstadoPaqueteModel.sucursal_id == self._sucursal)
        return {
            "registrados": await self._escalar(registrados),
            "ingresados": await self._escalar(ingresados),
            "entregados": await self._escalar(
                eventos.where(EventoEntregaModel.resultado == ResultadoEventoEntregaEnum.EXITOSO.value)
            ),
            "visitas_fallidas": await self._escalar(
                eventos.where(EventoEntregaModel.resultado == ResultadoEventoEntregaEnum.FALLIDO.value)
            ),
        }

    async def recorridos_por_estado(self, fecha: date) -> dict[str, int]:
        stmt = select(RecorridoModel.estado, func.count()).where(RecorridoModel.fecha == fecha)
        if self._sucursal:
            stmt = stmt.where(RecorridoModel.sucursal_origen_id == self._sucursal)
        filas = await self.db.execute(stmt.group_by(RecorridoModel.estado))
        return {estado: int(cantidad) for estado, cantidad in filas.all()}

    async def contar_repartidores_en_ruta(self) -> int:
        stmt = select(func.count(func.distinct(RecorridoModel.repartidor_id))).where(
            RecorridoModel.estado == EstadoRecorridoEnum.EN_CURSO.value
        )
        if self._sucursal:
            stmt = stmt.where(RecorridoModel.sucursal_origen_id == self._sucursal)
        return await self._escalar(stmt)

    async def listar_sucursales(self) -> list[Any]:
        return list((await self.db.execute(select(SucursalModel).order_by(SucursalModel.nombre))).scalars().all())

    # --- Listado ------------------------------------------------------------

    def _filtrado(
        self,
        *,
        buscar: str | None,
        estados: tuple[str, ...] | None,
        especial: str | None,
        sucursal_id: int | None,
        devolucion: bool | None = None,
        tipo_entrega: str | None,
        desde: datetime | None,
        hasta: datetime | None,
    ):
        stmt = select(PaqueteModel).join(EnvioModel, PaqueteModel.envio_id == EnvioModel.id)
        if buscar:
            patron = f"%{buscar.strip()}%"
            stmt = stmt.where(
                or_(
                    PaqueteModel.numero_paquete.ilike(patron),
                    PaqueteModel.descripcion.ilike(patron),
                    EnvioModel.token_seguimiento.ilike(patron),
                    EnvioModel.remitente_nombre.ilike(patron),
                    EnvioModel.remitente_documento.ilike(patron),
                    EnvioModel.destinatario_nombre.ilike(patron),
                    EnvioModel.destinatario_telefono.ilike(patron),
                    EnvioModel.ciudad_destino.ilike(patron),
                    EnvioModel.direccion_destino.ilike(patron),
                )
            )
        if estados:
            condicion = PaqueteModel.estado.in_(estados)
            if devolucion is True:
                condicion = or_(condicion, PaqueteModel.en_devolucion.is_(True))
            stmt = stmt.where(condicion)
            if devolucion is False:
                stmt = stmt.where(PaqueteModel.en_devolucion.is_(False))
        if especial in ESPECIALES:
            stmt = stmt.where(ESPECIALES[especial]())
        if sucursal_id:
            stmt = stmt.where(
                or_(
                    PaqueteModel.sucursal_actual_id == sucursal_id,
                    PaqueteModel.sucursal_origen_id == sucursal_id,
                    EnvioModel.sucursal_destino_id == sucursal_id,
                )
            )
        if tipo_entrega:
            stmt = stmt.where(EnvioModel.tipo_entrega == tipo_entrega)
        if desde:
            stmt = stmt.where(PaqueteModel.created_at >= desde)
        if hasta:
            stmt = stmt.where(PaqueteModel.created_at < hasta)
        return stmt

    async def listar_paquetes(
        self,
        *,
        buscar: str | None = None,
        estados: tuple[str, ...] | None = None,
        devolucion: bool | None = None,
        especial: str | None = None,
        sucursal_id: int | None = None,
        tipo_entrega: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        orden: str = "movimiento",
        offset: int = 0,
        limite: int = 25,
    ) -> tuple[list[Any], int]:
        base = self._filtrado(
            buscar=buscar, estados=estados, devolucion=devolucion, especial=especial, sucursal_id=sucursal_id,
            tipo_entrega=tipo_entrega, desde=desde, hasta=hasta,
        )
        total = await self._escalar(select(func.count()).select_from(base.with_only_columns(PaqueteModel.id).subquery()))
        stmt = (
            base.options(
                contains_eager(PaqueteModel.envio).selectinload(EnvioModel.sucursal_destino),
                selectinload(PaqueteModel.sucursal_actual),
            )
            .order_by(*ORDENES.get(orden, ORDENES["movimiento"]))
            .offset(offset)
            .limit(limite)
        )
        paquetes = list((await self.db.execute(stmt)).unique().scalars().all())
        return paquetes, total

    async def datos_operativos(self, paquetes: list[Any]) -> dict[uuid.UUID, dict[str, Any]]:
        """Recorrido vigente, visitas fallidas, alertas y reclamos en curso de cada paquete."""
        ids = [p.id for p in paquetes]
        datos: dict[uuid.UUID, dict[str, Any]] = {
            p.id: {"asignacion": None, "fallidos": 0, "alerta": False, "faltante": False, "reclamos": 0} for p in paquetes
        }
        if not ids:
            return datos

        asignaciones = await self.db.execute(
            select(RecorridoPaqueteModel)
            .join(RecorridoModel, RecorridoPaqueteModel.recorrido_id == RecorridoModel.id)
            .where(RecorridoPaqueteModel.paquete_id.in_(ids))
            .options(
                contains_eager(RecorridoPaqueteModel.recorrido)
                .joinedload(RecorridoModel.repartidor)
                .joinedload(RepartidorModel.usuario)
            )
            .order_by(RecorridoModel.fecha.desc(), RecorridoPaqueteModel.created_at.desc())
        )
        for asignacion in asignaciones.unique().scalars().all():
            if datos[asignacion.paquete_id]["asignacion"] is None:
                datos[asignacion.paquete_id]["asignacion"] = asignacion

        fallidos = await self.db.execute(
            select(EventoEntregaModel.paquete_id, func.count())
            .where(
                EventoEntregaModel.paquete_id.in_(ids),
                EventoEntregaModel.resultado == ResultadoEventoEntregaEnum.FALLIDO.value,
            )
            .group_by(EventoEntregaModel.paquete_id)
        )
        for paquete_id, cantidad in fallidos.all():
            datos[paquete_id]["fallidos"] = int(cantidad)

        alertas = await self.db.execute(
            select(AlertaRecorridoModel.paquete_id)
            .where(AlertaRecorridoModel.paquete_id.in_(ids), AlertaRecorridoModel.resuelta.is_(False))
            .distinct()
        )
        for (paquete_id,) in alertas.all():
            datos[paquete_id]["alerta"] = True

        envios = {p.envio_id for p in paquetes}
        reclamos = await self.db.execute(
            select(ReclamoModel.envio_id, ReclamoModel.paquete_id).where(
                ReclamoModel.envio_id.in_(envios), ReclamoModel.estado.in_(ESTADOS_RECLAMO_EN_CURSO)
            )
        )
        for envio_id, paquete_id in reclamos.all():
            for paquete in paquetes:
                if paquete.envio_id == envio_id and paquete_id in (None, paquete.id):
                    datos[paquete.id]["reclamos"] += 1
        return datos

    # --- Trazabilidad -------------------------------------------------------

    async def obtener_paquete(self, numero_paquete: str) -> Any | None:
        stmt = (
            select(PaqueteModel)
            .where(func.upper(PaqueteModel.numero_paquete) == numero_paquete.strip().upper())
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
                joinedload(PaqueteModel.sucursal_origen),
            )
        )
        return (await self.db.execute(stmt)).unique().scalar_one_or_none()

    async def historial(self, paquete_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(HistorialEstadoPaqueteModel)
            .where(HistorialEstadoPaqueteModel.paquete_id == paquete_id)
            .options(joinedload(HistorialEstadoPaqueteModel.usuario), joinedload(HistorialEstadoPaqueteModel.sucursal))
            .order_by(HistorialEstadoPaqueteModel.created_at, HistorialEstadoPaqueteModel.id)
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def eventos_entrega(self, paquete_id: uuid.UUID) -> list[tuple[Any, bool]]:
        """Eventos de entrega o retiro, cada uno con un indicador de si tiene firma."""
        stmt = (
            select(EventoEntregaModel, EventoEntregaModel.firma_imagen.is_not(None))
            .where(EventoEntregaModel.paquete_id == paquete_id)
            .options(
                defer(EventoEntregaModel.firma_imagen),
                joinedload(EventoEntregaModel.usuario_registro),
                joinedload(EventoEntregaModel.sucursal),
            )
            .order_by(EventoEntregaModel.created_at)
        )
        return [(evento, bool(con_firma)) for evento, con_firma in (await self.db.execute(stmt)).unique().all()]

    async def asignaciones(self, paquete_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(RecorridoPaqueteModel)
            .where(RecorridoPaqueteModel.paquete_id == paquete_id)
            .options(
                joinedload(RecorridoPaqueteModel.recorrido).joinedload(RecorridoModel.repartidor).joinedload(RepartidorModel.usuario),
                joinedload(RecorridoPaqueteModel.recorrido).joinedload(RecorridoModel.sucursal_origen),
            )
            .order_by(RecorridoPaqueteModel.created_at)
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def alertas(self, paquete_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(AlertaRecorridoModel)
            .where(AlertaRecorridoModel.paquete_id == paquete_id)
            .order_by(AlertaRecorridoModel.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def reclamos_del_envio(self, envio_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(ReclamoModel)
            .where(ReclamoModel.envio_id == envio_id)
            .options(joinedload(ReclamoModel.paquete), joinedload(ReclamoModel.usuario_resolucion))
            .order_by(ReclamoModel.created_at)
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def notificaciones_del_envio(self, envio_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.envio_id == envio_id)
            .order_by(NotificacionEnvioModel.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def paquetes_del_envio(self, envio_id: uuid.UUID) -> list[Any]:
        stmt = (
            select(PaqueteModel)
            .where(PaqueteModel.envio_id == envio_id)
            .order_by(PaqueteModel.created_at, PaqueteModel.numero_paquete)
        )
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def obtener_firma(self, evento_id: uuid.UUID) -> tuple[bytes, str] | None:
        fila = (
            await self.db.execute(
                select(EventoEntregaModel.firma_imagen, EventoEntregaModel.firma_content_type).where(
                    EventoEntregaModel.id == evento_id
                )
            )
        ).first()
        if not fila or not fila[0]:
            return None
        return bytes(fila[0]), fila[1] or "image/png"
