from typing import Any, Protocol
from uuid import UUID


class IRepositorioReclamos(Protocol):
    """Protocolo de acceso a datos de los reclamos (HU07).

    El envío se resuelve con `IRepositorioEnvios.obtener_por_token` (el mismo
    que usa HU04): un reclamo siempre se inicia desde un token válido.
    """

    async def listar_por_envio(self, envio_id: UUID) -> list[Any]:
        """Reclamos de un envío, del más reciente al más antiguo, con su paquete cargado."""
        ...

    async def crear(self, reclamo: Any) -> Any:
        """Persiste el reclamo y lo devuelve con sus relaciones cargadas."""
        ...

    async def listar(
        self,
        estado: str | None = None,
        tipo: str | None = None,
        token_seguimiento: str | None = None,
        sucursal_id: int | None = None,
    ) -> list[Any]:
        """Bandeja de gestión, filtrable por estado, tipo y token del envío."""
        ...

    async def obtener_por_id(self, id: UUID) -> Any | None: ...

    async def actualizar(self, reclamo: Any) -> Any:
        """Persiste los cambios ya aplicados y devuelve el reclamo recargado."""
        ...
