from typing import Any, Protocol
from uuid import UUID


class IRepositorioNotificaciones(Protocol):
    """Protocolo que define el acceso a datos para auditoría de notificaciones (HU05)."""

    async def obtener_avisos_visita(self, evento_id: UUID) -> list[Any]:
        """Avisos por canal generados por una visita fallida (HU12)."""
        ...

    async def tomar_notificacion(self, notificacion_id: UUID) -> bool:
        """Reserva atómicamente un intento pendiente/fallido; uno enviado nunca se vuelve a enviar."""
        ...

    async def finalizar_notificacion(
        self, notificacion_id: UUID, estado: str, proveedor_mensaje_id: str | None, error_detalle: str | None
    ) -> None: ...

    async def registrar(self, notificacion: Any) -> Any:
        """Persiste un nuevo intento o log de notificación."""
        ...

    async def registrar_intento(
        self,
        envio_id: UUID,
        canal: str,
        destinatario_tipo: str,
        destino: str,
        tipo_aviso: str = ...,
        paquete_id: UUID | None = None,
    ) -> Any:
        """Crea un intento pendiente para un canal y destinatario."""
        ...

    async def obtener_por_id(self, notificacion_id: UUID) -> Any | None: ...

    async def obtener_por_envio_id(self, envio_id: UUID) -> list[Any]:
        """Recupera el historial de notificaciones asociado a un envío."""
        ...

    async def obtener_envio_por_token(self, token: str) -> Any | None:
        """Envío con sus paquetes, para reconstruir los datos de un reintento."""
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

    async def obtener_paquete_aviso(self, paquete_id: UUID) -> Any | None:
        """Paquete con su envío y sucursales, para armar un aviso por hito."""
        ...

    async def avisos_recientes_de_envio(self, envio_id: UUID, tipo_aviso: str, desde: Any) -> list[Any]:
        """Avisos del mismo hito para el envío, creados desde `desde`."""
        ...

    async def contar_visitas_fallidas(self, paquete_id: UUID) -> int: ...

    async def ultima_entrega(self, paquete_id: UUID) -> Any | None: ...

    async def obtener_sucursal(self, sucursal_id: int) -> Any | None: ...
