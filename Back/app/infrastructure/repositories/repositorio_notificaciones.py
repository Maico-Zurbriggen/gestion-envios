from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domain.constants.estados_logistica import EstadoNotificacionEnum
from app.infrastructure.db.models import EnvioModel, EventoEntregaModel, NotificacionEnvioModel

VENCIMIENTO_RESERVA = timedelta(minutes=5)
"""Una reserva más antigua se considera abandonada (proceso caído a mitad del envío)."""


class RepositorioNotificaciones:
    """Implementación SQLAlchemy para el almacenamiento de notificaciones y logs (HU05)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_avisos_visita(self, evento_id: UUID) -> list[NotificacionEnvioModel]:
        """Avisos (uno por canal) generados por una visita fallida de HU12."""
        resultado = await self.db.execute(
            select(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.evento_entrega_id == evento_id)
            .options(
                joinedload(NotificacionEnvioModel.envio),
                joinedload(NotificacionEnvioModel.evento_entrega).joinedload(EventoEntregaModel.paquete),
            )
            .order_by(NotificacionEnvioModel.canal)
        )
        return list(resultado.unique().scalars().all())

    async def tomar_notificacion(self, notificacion_id: UUID) -> bool:
        """Reserva atómicamente un intento pendiente/fallido; uno enviado nunca se vuelve a enviar."""
        ahora = datetime.now(UTC)
        resultado = await self.db.execute(
            update(NotificacionEnvioModel)
            .where(
                NotificacionEnvioModel.id == notificacion_id,
                NotificacionEnvioModel.estado.in_(
                    [EstadoNotificacionEnum.PENDIENTE.value, EstadoNotificacionEnum.FALLIDO.value]
                ),
                or_(
                    NotificacionEnvioModel.procesando_at.is_(None),
                    NotificacionEnvioModel.procesando_at < ahora - VENCIMIENTO_RESERVA,
                ),
            )
            .values(procesando_at=ahora)
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        return resultado.rowcount == 1

    async def finalizar_notificacion(
        self,
        notificacion_id: UUID,
        estado: str,
        proveedor_mensaje_id: str | None,
        error_detalle: str | None,
    ) -> None:
        await self.db.execute(
            update(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.id == notificacion_id)
            .values(
                estado=estado,
                proveedor_mensaje_id=proveedor_mensaje_id,
                error_detalle=error_detalle,
                procesando_at=None,
                updated_at=datetime.now(UTC),
            )
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()

    async def registrar(self, notificacion: NotificacionEnvioModel) -> NotificacionEnvioModel:
        """Persiste una entidad de notificación en la base de datos."""
        self.db.add(notificacion)
        await self.db.commit()
        await self.db.refresh(notificacion)
        return notificacion

    async def registrar_intento(
        self, envio_id: UUID, canal: str, destinatario_tipo: str, destino: str
    ) -> NotificacionEnvioModel:
        return await self.registrar(
            NotificacionEnvioModel(
                envio_id=envio_id,
                canal=canal,
                destinatario_tipo=destinatario_tipo,
                destino=destino[:150],
                estado=EstadoNotificacionEnum.PENDIENTE.value,
            )
        )

    async def obtener_por_id(self, notificacion_id: UUID) -> NotificacionEnvioModel | None:
        resultado = await self.db.execute(
            select(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.id == notificacion_id)
            .execution_options(populate_existing=True)
        )
        return resultado.scalar_one_or_none()

    async def obtener_por_envio_id(self, envio_id: UUID) -> list[NotificacionEnvioModel]:
        """Obtiene todas las notificaciones registradas para un envío ordenadas por fecha."""
        stmt = (
            select(NotificacionEnvioModel)
            .where(NotificacionEnvioModel.envio_id == envio_id)
            .order_by(NotificacionEnvioModel.created_at.asc(), NotificacionEnvioModel.canal)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def obtener_envio_por_token(self, token: str) -> EnvioModel | None:
        resultado = await self.db.execute(
            select(EnvioModel)
            .where(EnvioModel.token_seguimiento == token)
            .options(selectinload(EnvioModel.paquetes))
        )
        return resultado.scalar_one_or_none()

    async def actualizar_estado(
        self,
        notificacion_id: UUID,
        estado: str,
        proveedor_mensaje_id: str | None = None,
        error_detalle: str | None = None,
    ) -> NotificacionEnvioModel | None:
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
