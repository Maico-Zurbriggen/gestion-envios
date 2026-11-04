"""Contratos del mapa: recorrido por calles y ubicación de direcciones."""

from pydantic import Field

from app.contracts.common import ApiModel


class PuntoData(ApiModel):
    latitud: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(..., ge=-180, le=180, allow_inf_nan=False)


class TrayectoRequest(ApiModel):
    puntos: list[PuntoData] = Field(..., min_length=2, max_length=100, description="En el orden de visita.")


class TrayectoData(ApiModel):
    geometria: list[tuple[float, float]] = Field(..., description="Puntos [longitud, latitud] para dibujar.")
    distancia_m: float
    duracion_s: float
    estimado: bool = Field(..., description="True si no se usó OSRM: línea recta y tiempo aproximado.")


class TrayectoResponse(ApiModel):
    status: str = "success"
    data: TrayectoData


class UbicacionData(ApiModel):
    latitud: float
    longitud: float
    texto: str
    precision: str = Field(..., description="'direccion', 'calle' o 'ciudad' (centro de la localidad).")
    fuente: str


class UbicacionResponse(ApiModel):
    status: str = "success"
    data: UbicacionData
