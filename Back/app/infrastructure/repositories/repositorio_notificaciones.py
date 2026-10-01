from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import NotificacionEnvioModel


class RepositorioNotificaciones:
    """Implementación SQLAlchemy para el almacenamiento de notificaciones y logs (HU05)."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
