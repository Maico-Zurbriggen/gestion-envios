from datetime import datetime

from app.contracts.common import ApiModel


class PaqueteSeguimientoData(ApiModel):
    """Vista pública de un paquete (HU04). Deliberadamente no incluye datos
    de contacto de remitente/destinatario: el endpoint no requiere
    autenticación, así que cualquiera con el token podría verlos."""

    numero_paquete: str
    estado: str
    descripcion: str
    observaciones: str | None
    fecha_registro: datetime
    ultima_actualizacion: datetime


class SeguimientoData(ApiModel):
    """`destino` ya viene armado como un único string legible (dirección
    completa o sucursal + dirección) para que la vista pública no tenga que
    decidir el formato. `paquetes` incluye todos los del envío asociado al
    token (HU04 Escenario 2), no uno solo."""

    token_seguimiento: str
    destino: str
    paquetes: list[PaqueteSeguimientoData]


class SeguimientoResponse(ApiModel):
    status: str = "success"
    data: SeguimientoData
