from typing import Protocol

from app.contracts.sucursales import ListarSucursalesResponse, OpcionesRetiroResponse


class IServicioSucursales(Protocol):
    """Protocolo del servicio de consulta del catálogo de sucursales (HU03) y de
    las opciones de retiro de un envío (HU09)."""

    async def listar_sucursales(
        self,
        provincia: str | None = None,
        ciudad: str | None = None,
    ) -> ListarSucursalesResponse:
        """Catálogo de sucursales, opcionalmente filtrado por provincia y/o ciudad."""
        ...

    async def obtener_opciones_retiro(self, token: str) -> OpcionesRetiroResponse:
        """Sucursales donde se puede retirar el envío asociado a un token (HU09)."""
        ...
