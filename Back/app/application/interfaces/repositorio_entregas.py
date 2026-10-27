from typing import Any, Protocol
from uuid import UUID


class IRepositorioEntregas(Protocol):
    """Protocolo que define el acceso a datos para retiros y entregas de paquetes (HU13)."""

    async def obtener_por_operacion(self, operacion_id: UUID) -> Any | None: ...

    async def obtener_evento(self, evento_id: UUID) -> Any | None: ...

    async def buscar_paquete_por_id_o_codigo(self, id_o_codigo: str) -> Any | None:
        """Busca un paquete por su ID (UUID) o por su código alfanumérico (numero_paquete).

        Carga las relaciones necesarias con el envío asociado y las sucursales.
        """
        ...

    async def registrar_retiro_paquete(
        self,
        paquete_id: UUID,
        nuevo_estado: str,
        evento_entrega: Any,
        historial_estado: Any,
        sucursal_actual_id: int | None = None,
    ) -> Any:
        """Actualiza el estado del paquete y persiste el evento de entrega y el historial en una sola transacción."""
        ...
