from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.constants.estados_logistica import CanalNotificacionEnum, EstadoNotificacionEnum
from app.infrastructure.db.models import EventoEntregaModel, NotificacionEnvioModel


class RepositorioNotificaciones:
    """Implementación SQLAlchemy para el almacenamiento de notificaciones y logs (HU05)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_aviso_visita(self, evento_id: UUID) -> Optional[NotificacionEnvioModel]:
        resultado = await self.db.execute(
            select(NotificacionEnvioModel).where(
                NotificacionEnvioModel.evento_entrega_id == evento_id,
                NotificacionEnvioModel.canal == CanalNotificacionEnum.EMAIL.value,
            ).options(joinedload(NotificacionEnvioModel.envio),
                      joinedload(NotificacionEnvioModel.evento_entrega).joinedload(EventoEntregaModel.paquete))
        )
        return resultado.unique().scalar_one_or_none()

    async def tomar_aviso_visita(self, notificacion_id: UUID) -> bool:
        resultado = await self.db.execute(
            update(NotificacionEnvioModel).where(
                NotificacionEnvioModel.id == notificacion_id,
                NotificacionEnvioModel.evento_entrega_id.is_not(None),
                NotificacionEnvioModel.estado.in_([EstadoNotificacionEnum.PENDIENTE.value,
                                                  EstadoNotificacionEnum.FALLIDO.value]),
                NotificacionEnvioModel.procesando_at.is_(None),
            ).values(procesando_at=datetime.now(UTC))
        )
        await self.db.commit()
        return resultado.rowcount == 1

    async def finalizar_aviso_visita(self, notificacion_id: UUID, estado: str,
                                   proveedor_mensaje_id: Optional[str], error_detalle: Optional[str]) -> None:
        await self.db.execute(
            update(NotificacionEnvioModel).where(NotificacionEnvioModel.id == notificacion_id)
            .values(estado=estado, proveedor_mensaje_id=proveedor_mensaje_id,
                    error_detalle=error_detalle, procesando_at=None)
        )
        await self.db.commit()

    async def registrar(self, notificacion: NotificacionEnvioModel) -> NotificacionEnvioModel:
        """Persiste una entidad de notificación en la base de datos."""
        self.db.add(notificacion)
        await self.db.commit()
        await self.db.refresh(notificacion)
        return notificacion

    async def obtener_por_envio_id(self, envio_id: UUID) -> List[NotificacionEnvioModel]:
        """Obtiene todas las notificaciones registradas para un envío ordenadas por fecha."""
        stmt = (
            select(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.envio_id == envio_id)
            .order_by(NotificacionEnvioModel.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def actualizar_estado(
        self,
        notificacion_id: UUID,
        estado: str,
        proveedor_mensaje_id: Optional[str] = None,
        error_detalle: Optional[str] = None,
    ) -> Optional[NotificacionEnvioModel]:
        """Actualiza el estado de envío y los metadatos de respuesta del proveedor."""
        stmt = select(NotificacionEnvioModel).where(NotificacionEnvioModel.id == notificacion_id)
        result = await self.db.execute(stmt)
        notificacion = result.scalar_one_or_none()
        if notificacion:
            notificacion.estado = estado
            if proveedor_mensaje_id is not None:
                notificacion.proveedor_mensaje_id = proveedor_mensaje_id
            if error_detalle is not None:
                notificacion.error_detalle = error_detalle
            await self.db.commit()
            await self.db.refresh(notificacion)
        return notificacion
