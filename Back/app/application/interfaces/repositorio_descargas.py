from datetime import date
from typing import Any, Protocol
from uuid import UUID


class IRepositorioDescargas(Protocol):
    """Acceso a datos del control de descarga en la sucursal de destino."""

    async def recorridos_desde(
        self,
        desde: date,
        estados: tuple[str, ...],
        *,
        sucursal_origen_id: int | None = None,
        excluir_origen_id: int | None = None,
        tipo_distancia: str | None = None,
    ) -> list[Any]:
        """Recorridos desde esa fecha, con repartidor, origen y paquetes cargados."""
        ...

    async def controles_de_sucursal(self, sucursal_id: int, recorrido_ids: list[UUID], tipo: str) -> dict[UUID, Any]:
        """Controles existentes de esa sucursal, por recorrido, con sus lecturas."""
        ...

    async def obtener_control(self, id: UUID) -> Any | None: ...

    async def obtener_control_por(self, recorrido_id: UUID, sucursal_id: int, tipo: str) -> Any | None: ...

    async def obtener_recorrido(self, id: UUID) -> Any | None:
        """Recorrido con sus paquetes (y cada paquete con su envío) para actualizarlo."""
        ...

    async def obtener_sucursal(self, id: int) -> Any | None: ...

    async def paquete_por_numero(self, numero: str) -> Any | None: ...

    async def tiene_alerta_abierta(self, paquete_id: UUID, motivo: str) -> bool: ...

    async def agregar(self, entidad: Any) -> None: ...

    async def confirmar(self) -> None: ...
