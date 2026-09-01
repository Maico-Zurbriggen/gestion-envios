from typing import Protocol

from app.contracts.sucursales import ListarSucursalesResponse


class IServicioSucursales(Protocol):
    """Protocolo del servicio de consulta del catálogo de sucursales."""

    async def listar_sucursales(self) -> ListarSucursalesResponse: ...
