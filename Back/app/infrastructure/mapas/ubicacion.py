"""Ubicación de direcciones argentinas en cascada, como en Rumbo.

1. Georef (API pública del Estado, sin clave): la dirección con altura, validando
   que la calle sea de esa localidad (Georef no tiene todas las calles y puede
   devolver una homónima de otra ciudad).
2. Nominatim (OpenStreetMap), si Georef no la encuentra: máximo 1 consulta por
   segundo según su política de uso.
3. El centro de la localidad (Georef), para que al menos el mapa quede cerca.
"""

import asyncio
import logging
import time
import unicodedata
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AGENTE = "GestionEnvios/1.0 (ubicacion de entregas)"
_cache: dict[str, "Ubicacion | None"] = {}
_turno_nominatim = asyncio.Lock()
_ultima_nominatim = 0.0


@dataclass(frozen=True)
class Ubicacion:
    latitud: float
    longitud: float
    texto: str
    precision: str
    """'direccion' (con altura), 'calle' o 'ciudad' (centro de la localidad)."""
    fuente: str


def _normalizar(texto: str | None) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


async def _georef_direccion(cliente: httpx.AsyncClient, calle: str, ciudad: str, provincia: str) -> Ubicacion | None:
    params = {"direccion": calle, "max": 5, "aplanar": "true"}
    if provincia:
        params["provincia"] = provincia
    respuesta = await cliente.get(f"{settings.GEOREF_URL.rstrip('/')}/direcciones", params=params)
    respuesta.raise_for_status()
    buscada = _normalizar(ciudad)
    for item in respuesta.json().get("direcciones") or []:
        localidad = _normalizar(item.get("localidad_censal_nombre") or item.get("departamento_nombre"))
        nomenclatura = _normalizar(item.get("nomenclatura"))
        if buscada and localidad != buscada and buscada not in nomenclatura:
            continue
        lat, lon = item.get("ubicacion_lat"), item.get("ubicacion_lon")
        if lat is None or lon is None:
            continue
        return Ubicacion(lat, lon, item.get("nomenclatura") or calle, "direccion" if item.get("altura_valor") else "calle", "Georef")
    return None


async def _georef_localidad(cliente: httpx.AsyncClient, ciudad: str, provincia: str) -> Ubicacion | None:
    params = {"nombre": ciudad, "max": 1, "aplanar": "true"}
    if provincia:
        params["provincia"] = provincia
    respuesta = await cliente.get(f"{settings.GEOREF_URL.rstrip('/')}/localidades", params=params)
    respuesta.raise_for_status()
    item = (respuesta.json().get("localidades") or [None])[0]
    if not item or item.get("centroide_lat") is None:
        return None
    texto = ", ".join(filter(None, [item.get("nombre"), item.get("provincia_nombre")]))
    return Ubicacion(item["centroide_lat"], item["centroide_lon"], texto, "ciudad", "Georef")


async def _nominatim(cliente: httpx.AsyncClient, consulta: str) -> Ubicacion | None:
    global _ultima_nominatim
    async with _turno_nominatim:
        espera = _ultima_nominatim + 1.1 - time.monotonic()
        if espera > 0:
            await asyncio.sleep(espera)
        _ultima_nominatim = time.monotonic()
        respuesta = await cliente.get(
            f"{settings.NOMINATIM_URL.rstrip('/')}/search",
            params={"q": consulta, "format": "jsonv2", "limit": 1, "countrycodes": "ar", "addressdetails": 1},
        )
    respuesta.raise_for_status()
    item = (respuesta.json() or [None])[0]
    if not item:
        return None
    precision = "direccion" if (item.get("address") or {}).get("house_number") else "calle"
    return Ubicacion(float(item["lat"]), float(item["lon"]), item.get("display_name", consulta), precision, "OpenStreetMap")


async def ubicar_direccion(calle: str, altura: str, ciudad: str, provincia: str) -> Ubicacion | None:
    """Coordenadas de una dirección argentina, o `None` si no se encuentra ni la ciudad."""
    direccion = " ".join(filter(None, [calle.strip(), altura.strip()]))
    clave = _normalizar(f"{direccion}|{ciudad}|{provincia}")
    if clave in _cache:
        return _cache[clave]
    resultado: Ubicacion | None = None
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": AGENTE, "Accept-Language": "es-AR,es"}) as cliente:
        pasos = []
        if settings.GEOREF_HABILITADO and direccion:
            pasos.append(lambda: _georef_direccion(cliente, direccion, ciudad, provincia))
        if settings.NOMINATIM_URL.strip() and direccion:
            pasos.append(lambda: _nominatim(cliente, ", ".join(filter(None, [direccion, ciudad, provincia, "Argentina"]))))
        if settings.GEOREF_HABILITADO and ciudad:
            pasos.append(lambda: _georef_localidad(cliente, ciudad, provincia))
        for paso in pasos:
            try:
                resultado = await paso()
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as error:
                logger.warning("No se pudo consultar un servicio de ubicación: %s", error)
                continue
            if resultado:
                break
    if resultado and resultado.precision != "ciudad":
        _cache[clave] = resultado
    return resultado
