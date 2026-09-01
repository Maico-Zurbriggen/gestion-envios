from datetime import datetime

from app.contracts.common import ApiModel


class PaqueteSeguimientoData(ApiModel):
    numero_paquete: str
    estado: str
    descripcion: str
    observaciones: str | None
    fecha_registro: datetime
    ultima_actualizacion: datetime


class SeguimientoData(ApiModel):
    token_seguimiento: str
    destino: str
    paquetes: list[PaqueteSeguimientoData]


class SeguimientoResponse(ApiModel):
    status: str = "success"
    data: SeguimientoData
