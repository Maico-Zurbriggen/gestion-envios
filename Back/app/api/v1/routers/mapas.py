"""Mapa: recorrido por calles (OSRM) y ubicación de direcciones (Georef + Nominatim)."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import obtener_usuario_actual
from app.contracts.mapas import TrayectoData, TrayectoRequest, TrayectoResponse, UbicacionData, UbicacionResponse
from app.core.exceptions import NotFoundException
from app.infrastructure.mapas.rutas import calcular_trayecto
from app.infrastructure.mapas.ubicacion import ubicar_direccion

router = APIRouter(prefix="/mapa", tags=["Mapa"])


@router.post(
    "/trayecto",
    response_model=TrayectoResponse,
    summary="Recorrido por calles entre puntos, en orden",
    description="Con OSRM si está configurado; si no, línea recta con distancia y tiempo estimados.",
)
async def trayecto(datos: TrayectoRequest, _usuario=Depends(obtener_usuario_actual)):
    resultado = await calcular_trayecto([(p.latitud, p.longitud) for p in datos.puntos])
    return TrayectoResponse(data=TrayectoData(
        geometria=resultado.geometria, distancia_m=resultado.distancia_m,
        duracion_s=resultado.duracion_s, estimado=resultado.estimado,
    ))


@router.get(
    "/ubicar",
    response_model=UbicacionResponse,
    summary="Ubicar una dirección argentina",
    description="Georef (Estado Argentino) y, si no la encuentra, OpenStreetMap. Es pública: la usa el registro de envíos.",
)
async def ubicar(
    calle: str = Query("", max_length=150),
    altura: str = Query("", max_length=20),
    ciudad: str = Query(..., min_length=2, max_length=100),
    provincia: str = Query("", max_length=100),
):
    resultado = await ubicar_direccion(calle, altura, ciudad, provincia)
    if resultado is None:
        raise NotFoundException("No encontramos la dirección ni la ciudad. Revisá cómo están escritas.")
    return UbicacionResponse(data=UbicacionData(
        latitud=resultado.latitud, longitud=resultado.longitud, texto=resultado.texto,
        precision=resultado.precision, fuente=resultado.fuente,
    ))
