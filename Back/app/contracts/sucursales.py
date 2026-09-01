
from app.contracts.common import ApiModel


class SucursalData(ApiModel):
    """Catálogo público de sucursales: alimenta el selector de "retiro en
    sucursal" de HU03 y, a futuro, la vista de HU09."""

    id: int
    nombre: str
    provincia: str
    ciudad: str
    direccion: str
    latitud: float | None = None
    longitud: float | None = None


class ListarSucursalesResponse(ApiModel):
    status: str = "success"
    data: list[SucursalData]
