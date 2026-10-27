from typing import Any, Protocol
from uuid import UUID


class IRepositorioNotificaciones(Protocol):
    """Protocolo que define el acceso a datos para auditoría de notificaciones (HU05)."""

    async def obtener_aviso_visita(self, evento_id: UUID) -> Any | None: ...

    async def tomar_aviso_visita(self, notificacion_id: UUID) -> bool:
        """Reserva atómicamente un aviso pendiente/fallido; un enviado nunca se vuelve a enviar."""
        ...

    async def finalizar_aviso_visita(self, notificacion_id: UUID, estado: str,
                                   proveedor_mensaje_id: str | None, error_detalle: str | None) -> None: ...

    async def registrar(self, notificacion: Any) -> Any:
        """Persiste un nuevo intento o log de notificación."""
        ...

    async def obtener_por_envio_id(self, envio_id: UUID) -> list[Any]:
        """Recupera el historial de notificaciones asociado a un envío."""
        ...

    async def actualizar_estado(
        self,
        notificacion_id: UUID,
        estado: str,
        proveedor_mensaje_id: str | None = None,
        error_detalle: str | None = None,
    ) -> Any | None:
        """Actualiza el estado y respuesta del proveedor de una notificación."""
        ...
