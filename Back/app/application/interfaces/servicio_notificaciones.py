from typing import Any, List, Protocol

from app.contracts.notificaciones import DatosNotificacionEnvio


class IServicioNotificaciones(Protocol):
    """Protocolo del servicio de notificaciones del sistema (HU05)."""

    async def notificar_nuevo_envio(self, datos: DatosNotificacionEnvio) -> List[Any]:
        """Envía las notificaciones de token de seguimiento al emisor y destinatario por correo.
        
        Registra cada intento (exitoso o fallido) en la base de datos sin propagar
        excepciones para no interrumpir el flujo principal de registro de envío.
        """
        ...
