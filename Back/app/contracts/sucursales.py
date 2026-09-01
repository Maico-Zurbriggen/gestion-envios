
from app.contracts.common import ApiModel


class SucursalData(ApiModel):
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
