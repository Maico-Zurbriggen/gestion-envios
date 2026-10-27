from datetime import datetime

from pydantic import Field

from app.contracts.common import ApiModel
from app.contracts.reparto import UbicacionData


class EventoSeguimientoData(ApiModel):
    estado_anterior: str | None
    estado: str
    fecha_hora: datetime
    descripcion: str


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
    historial: list[EventoSeguimientoData] = Field(default_factory=list)
    ubicacion_repartidor: UbicacionData | None = None


class SeguimientoData(ApiModel):
    """`destino` ya viene armado como un único string legible (dirección
    completa o sucursal + dirección) para que la vista pública no tenga que
    decidir el formato. `paquetes` incluye todos los del envío asociado al
    token (HU04 Escenario 2), no uno solo.

    `latitud_destino`/`longitud_destino` son las coordenadas fijas del
    destino. La última posición del repartidor se proporciona por paquete
    exclusivamente mientras esté pendiente en un recorrido EN_CURSO."""

    token_seguimiento: str
    tipo_entrega: str
    """`domicilio` o `sucursal`: habilita en la vista pública la consulta de sucursal de retiro (HU09)."""
    destino: str
    latitud_destino: float | None
    longitud_destino: float | None
    paquetes: list[PaqueteSeguimientoData]


class SeguimientoResponse(ApiModel):
    status: str = "success"
    data: SeguimientoData
