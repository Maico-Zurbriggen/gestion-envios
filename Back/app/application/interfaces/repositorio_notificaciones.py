from typing import Any, List, Optional, Protocol
from uuid import UUID


class IRepositorioNotificaciones(Protocol):
    """Protocolo que define el acceso a datos para auditoría de notificaciones (HU05)."""

    async def obtener_aviso_visita(self, evento_id: UUID) -> Optional[Any]: ...

    async def tomar_aviso_visita(self, notificacion_id: UUID) -> bool:
        """Reserva atómicamente un aviso pendiente/fallido; un enviado nunca se vuelve a enviar."""
        ...

    async def finalizar_aviso_visita(self, notificacion_id: UUID, estado: str,
                                   proveedor_mensaje_id: Optional[str], error_detalle: Optional[str]) -> None: ...

    async def registrar(self, notificacion: Any) -> Any:
        """Persiste un nuevo intento o log de notificación."""
        ...

    async def obtener_por_envio_id(self, envio_id: UUID) -> List[Any]:
        """Recupera el historial de notificaciones asociado a un envío."""
        ...

    async def actualizar_estado(
        self,
        notificacion_id: UUID,
        estado: str,
        proveedor_mensaje_id: Optional[str] = None,
        error_detalle: Optional[str] = None,
    ) -> Optional[Any]:
        """Actualiza el estado y respuesta del proveedor de una notificación."""
        ...
