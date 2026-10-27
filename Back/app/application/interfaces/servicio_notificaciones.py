from typing import Any, Protocol
from uuid import UUID

from app.contracts.notificaciones import DatosNotificacionEnvio, NotificacionesEnvioResponse


class IServicioNotificaciones(Protocol):
    """Protocolo del servicio de notificaciones del sistema (HU05 y aviso de visita de HU12)."""

    async def notificar_visita_fallida(self, evento_id: UUID) -> None: ...

    async def notificar_nuevo_envio(self, datos: DatosNotificacionEnvio) -> list[Any]:
        """Envía el token de seguimiento al emisor y destinatario por email y WhatsApp.

        Registra cada intento (exitoso o fallido) en la base de datos sin propagar
        excepciones para no interrumpir el flujo principal de registro de envío.
        """
        ...

    async def listar_por_token(self, token: str, mensaje: str | None = None) -> NotificacionesEnvioResponse:
        """Resultado auditado por canal y destinatario de un envío."""
        ...

    async def reintentar_por_token(self, token: str) -> NotificacionesEnvioResponse:
        """Reenvía únicamente los intentos pendientes o fallidos del envío."""
        ...
