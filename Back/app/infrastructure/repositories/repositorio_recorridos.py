import uuid
from datetime import date

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.application.interfaces.repositorio_recorridos import IRepositorioRecorridos
from app.core.exceptions import DuplicateEntryException
from app.domain.constants.estados_logistica import EstadoRecorridoPaqueteEnum, MotivoAlertaRecorridoEnum
from app.domain.rules.recorrido_rules import (
    ESTADOS_PAQUETE_LISTOS_PARA_DESPACHO,
    ESTADOS_RECORRIDO_ACTIVOS,
    ESTADOS_RECORRIDO_EDITABLES,
)
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    EnvioModel,
    PaqueteModel,
    PosicionActualRepartidorModel,
    RecorridoModel,
    RecorridoPaqueteModel,
    RepartidorModel,
    UsuarioModel,
)


class RepositorioRecorridos(IRepositorioRecorridos):
    """Acceso a datos de recorridos, paradas y alertas con SQLAlchemy (HU10)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Paquetes ---

    async def listar_paquetes_listos_en_sucursal(self, sucursal_id: int) -> list[PaqueteModel]:
        stmt = (
            select(PaqueteModel)
            .options(joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino))
            .where(
                PaqueteModel.sucursal_actual_id == sucursal_id,
                PaqueteModel.estado.in_(ESTADOS_PAQUETE_LISTOS_PARA_DESPACHO),
            )
            .order_by(PaqueteModel.numero_paquete)
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def buscar_paquetes_por_codigos(self, codigos: list[str]) -> list[PaqueteModel]:
        if not codigos:
            return []
        uuids = []
        for codigo in codigos:
            try:
                uuids.append(uuid.UUID(codigo))
            except ValueError:
                continue
        condiciones = [PaqueteModel.numero_paquete.in_(codigos)]
        if uuids:
            condiciones.append(PaqueteModel.id.in_(uuids))
        stmt = (
            select(PaqueteModel)
            .options(joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino))
            .where(or_(*condiciones))
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def paquetes_en_recorridos_activos(
        self, excluir_recorridos: set[uuid.UUID] | None = None
    ) -> dict[uuid.UUID, uuid.UUID]:
        stmt = (
            select(RecorridoPaqueteModel.paquete_id, RecorridoPaqueteModel.recorrido_id)
            .join(RecorridoModel, RecorridoPaqueteModel.recorrido_id == RecorridoModel.id)
            .where(
                RecorridoModel.estado.in_(ESTADOS_RECORRIDO_ACTIVOS),
                RecorridoPaqueteModel.estado_en_recorrido == EstadoRecorridoPaqueteEnum.PENDIENTE.value,
            )
        )
        if excluir_recorridos:
            stmt = stmt.where(RecorridoModel.id.not_in(excluir_recorridos))
        result = await self.db.execute(stmt)
        return {paquete_id: recorrido_id for paquete_id, recorrido_id in result.all()}

    # --- Repartidores ---

    async def listar_repartidores_disponibles(self, sucursal_id: int, tipo_distancia: str) -> list[RepartidorModel]:
        stmt = (
            select(RepartidorModel)
            .join(UsuarioModel, RepartidorModel.usuario_id == UsuarioModel.id)
            .options(joinedload(RepartidorModel.usuario))
            .where(
                RepartidorModel.sucursal_base_id == sucursal_id,
                RepartidorModel.tipo_reparto == tipo_distancia,
                RepartidorModel.activo.is_(True),
                UsuarioModel.estado == "Activo",
            )
            .order_by(UsuarioModel.nombre, UsuarioModel.id)
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def obtener_repartidor(self, usuario_id: uuid.UUID) -> RepartidorModel | None:
        stmt = (
            select(RepartidorModel)
            .options(joinedload(RepartidorModel.usuario))
            .where(RepartidorModel.usuario_id == usuario_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def repartidores_con_recorrido_activo(
        self,
        fecha: date,
        excluir_recorridos: set[uuid.UUID] | None = None,
    ) -> set[uuid.UUID]:
        stmt = select(RecorridoModel.repartidor_id).where(
            RecorridoModel.fecha == fecha,
            RecorridoModel.estado.in_(ESTADOS_RECORRIDO_ACTIVOS),
        )
        if excluir_recorridos:
            stmt = stmt.where(RecorridoModel.id.not_in(excluir_recorridos))
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    # --- Recorridos ---

    def _select_recorrido_completo(self):
        return select(RecorridoModel).options(
            selectinload(RecorridoModel.paquetes)
            .joinedload(RecorridoPaqueteModel.paquete)
            .joinedload(PaqueteModel.envio)
            .joinedload(EnvioModel.sucursal_destino),
            joinedload(RecorridoModel.repartidor).joinedload(RepartidorModel.usuario),
            joinedload(RecorridoModel.sucursal_origen),
        )

    async def listar_recorridos(
        self,
        sucursal_id: int | None = None,
        fecha: date | None = None,
        tipo_distancia: str | None = None,
        estado: str | None = None,
        repartidor_id: uuid.UUID | None = None,
    ) -> list[RecorridoModel]:
        stmt = self._select_recorrido_completo()
        if sucursal_id is not None:
            stmt = stmt.where(RecorridoModel.sucursal_origen_id == sucursal_id)
        if fecha is not None:
            stmt = stmt.where(RecorridoModel.fecha == fecha)
        if tipo_distancia:
            stmt = stmt.where(RecorridoModel.tipo_distancia == tipo_distancia)
        if estado:
            stmt = stmt.where(RecorridoModel.estado == estado)
        if repartidor_id is not None:
            stmt = stmt.where(RecorridoModel.repartidor_id == repartidor_id)
        stmt = stmt.order_by(RecorridoModel.fecha.desc(), RecorridoModel.created_at, RecorridoModel.id)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def obtener_recorrido(self, id: uuid.UUID) -> RecorridoModel | None:
        stmt = self._select_recorrido_completo().where(RecorridoModel.id == id).execution_options(
            populate_existing=True
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def bloquear_recorrido(self, id: uuid.UUID, repartidor_id: uuid.UUID) -> None:
        # Una escritura sin cambios toma un lock transaccional en PostgreSQL y SQLite.
        # SELECT FOR UPDATE por sí solo no protege en SQLite.
        await self.db.execute(
            update(RepartidorModel).where(RepartidorModel.usuario_id == repartidor_id)
            .values(activo=RepartidorModel.activo, updated_at=RepartidorModel.updated_at)
        )
        await self.db.execute(
            update(RecorridoModel)
            .where(RecorridoModel.id == id, RecorridoModel.repartidor_id == repartidor_id)
            .values(estado=RecorridoModel.estado, updated_at=RecorridoModel.updated_at)
        )

    async def obtener_posicion(self, repartidor_id: uuid.UUID) -> PosicionActualRepartidorModel | None:
        return await self.db.get(PosicionActualRepartidorModel, repartidor_id, populate_existing=True)

    async def actualizar_estado_paquete(self, paquete_id: uuid.UUID, anterior: str, nuevo: str,
                                       sucursal_id: int | None = None) -> None:
        resultado = await self.db.execute(
            update(PaqueteModel)
            .where(PaqueteModel.id == paquete_id, PaqueteModel.estado == anterior)
            .values(estado=nuevo, sucursal_actual_id=sucursal_id)
            .execution_options(synchronize_session="fetch")
        )
        if resultado.rowcount != 1:
            await self.db.rollback()
            raise DuplicateEntryException(message="El estado del paquete cambió. Volvé a consultar el recorrido.")

    async def listar_recorridos_editables(
        self, sucursal_id: int, fecha: date, tipo_distancia: str
    ) -> list[RecorridoModel]:
        stmt = self._select_recorrido_completo().where(
            RecorridoModel.sucursal_origen_id == sucursal_id,
            RecorridoModel.fecha == fecha,
            RecorridoModel.tipo_distancia == tipo_distancia,
            RecorridoModel.estado.in_(ESTADOS_RECORRIDO_EDITABLES),
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def listar_recorridos_activos_del_envio(self, envio_id: uuid.UUID) -> list[RecorridoModel]:
        stmt = self._select_recorrido_completo().where(
            RecorridoModel.estado.in_(ESTADOS_RECORRIDO_ACTIVOS),
            RecorridoModel.paquetes.any(
                RecorridoPaqueteModel.paquete.has(PaqueteModel.envio_id == envio_id)
            ),
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    # --- Alertas ---

    def _select_alerta_completa(self):
        return select(AlertaRecorridoModel).options(
            joinedload(AlertaRecorridoModel.paquete).joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino)
        )

    async def listar_alertas_pendientes_en_sucursal(self, sucursal_id: int) -> list[AlertaRecorridoModel]:
        stmt = (
            self._select_alerta_completa()
            .join(PaqueteModel, AlertaRecorridoModel.paquete_id == PaqueteModel.id)
            .where(
                AlertaRecorridoModel.resuelta.is_(False),
                PaqueteModel.sucursal_actual_id == sucursal_id,
                # Un faltante en la descarga no lo resuelve generar recorridos: lo revisa una persona.
                AlertaRecorridoModel.motivo != MotivoAlertaRecorridoEnum.FALTANTE_EN_DESCARGA.value,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def listar_alertas(
        self, sucursal_id: int | None = None, incluir_resueltas: bool = False
    ) -> list[AlertaRecorridoModel]:
        stmt = self._select_alerta_completa().join(PaqueteModel, AlertaRecorridoModel.paquete_id == PaqueteModel.id)
        if sucursal_id is not None:
            stmt = stmt.where(PaqueteModel.sucursal_actual_id == sucursal_id)
        if not incluir_resueltas:
            stmt = stmt.where(AlertaRecorridoModel.resuelta.is_(False))
        stmt = stmt.order_by(AlertaRecorridoModel.created_at.desc(), AlertaRecorridoModel.id)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def alertas_pendientes_de_paquetes(self, paquete_ids: list[uuid.UUID]) -> list[AlertaRecorridoModel]:
        if not paquete_ids:
            return []
        stmt = (
            self._select_alerta_completa()
            .where(AlertaRecorridoModel.resuelta.is_(False), AlertaRecorridoModel.paquete_id.in_(paquete_ids))
            .order_by(AlertaRecorridoModel.created_at, AlertaRecorridoModel.id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def obtener_alerta(self, id: uuid.UUID) -> AlertaRecorridoModel | None:
        stmt = self._select_alerta_completa().where(AlertaRecorridoModel.id == id).execution_options(
            populate_existing=True
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    # --- Unidad de trabajo ---

    async def agregar(self, entidad: object) -> None:
        self.db.add(entidad)

    async def eliminar(self, entidad: object) -> None:
        await self.db.delete(entidad)

    async def sincronizar(self) -> None:
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateEntryException(message="La operación entra en conflicto con un registro existente.") from exc

    async def confirmar(self) -> None:
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateEntryException(message="La operación entra en conflicto con un registro existente.") from exc
