from typing import Protocol

from app.contracts.sucursales import (
    GuardarSucursalRequest,
    ListarSucursalesAdminResponse,
    ListarSucursalesResponse,
    OpcionesRetiroResponse,
    SucursalAdminResponse,
)


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

    async def listar_admin(self) -> ListarSucursalesAdminResponse:
        """Todas las sucursales, también las inactivas, con cuántos usuarios las tienen habilitadas."""
        ...

    async def crear_sucursal(self, datos: GuardarSucursalRequest) -> SucursalAdminResponse: ...

    async def actualizar_sucursal(self, id: int, datos: GuardarSucursalRequest) -> SucursalAdminResponse: ...
