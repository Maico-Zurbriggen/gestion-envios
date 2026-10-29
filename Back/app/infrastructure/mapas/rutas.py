"""Recorridos por calles y rutas con OSRM, como en Rumbo.

`OSRM_URL` apunta a un OSRM con el mapa de Argentina: el propio (ver `deploy/osrm`,
recomendado en producción) o, por defecto, el servidor público de demostración,
que solo admite uso liviano (una consulta por segundo).

Nunca se inventan diagonales: si OSRM no responde, el trayecto se marca como
estimado y el mapa muestra solo las paradas.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.domain.rules.recorrido_rules import distancia_haversine_km

logger = logging.getLogger(__name__)

MAX_PUNTOS = 100
_turno_publico = asyncio.Lock()
_ultima_publica = 0.0


@dataclass(frozen=True)
class Trayecto:
    geometria: list[tuple[float, float]]
    """Puntos (longitud, latitud) para dibujar."""
    distancia_m: float
    duracion_s: float
    estimado: bool
    """`True` si no se usó OSRM: no hay geometría por calles y los valores son aproximados."""


def _coordenadas(puntos: list[tuple[float, float]]) -> str:
    return ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in puntos)


async def _consultar(ruta: str, params: dict[str, str] | None = None) -> dict | None:
    """GET a OSRM. Con el servidor público se respeta una consulta por segundo."""
    global _ultima_publica
    url = settings.OSRM_URL.strip().rstrip("/")
    if not url:
        return None
    try:
        if "project-osrm.org" in url:
            async with _turno_publico:
                espera = _ultima_publica + 1.05 - time.monotonic()
                if espera > 0:
                    await asyncio.sleep(espera)
                _ultima_publica = time.monotonic()
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "GestionEnvios/1.0"}) as cliente:
            respuesta = await cliente.get(f"{url}/{ruta}", params=params)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return datos if datos.get("code") == "Ok" else None
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("OSRM no respondió: %s", error)
        return None


async def calcular_trayecto(puntos: list[tuple[float, float]]) -> Trayecto:
    """Recorrido por calles que pasa por los puntos (latitud, longitud) en ese orden."""
    if 2 <= len(puntos) <= MAX_PUNTOS:
        datos = await _consultar(
            f"route/v1/driving/{_coordenadas(puntos)}",
            {"overview": "full", "geometries": "geojson", "steps": "false"},
        )
        try:
            ruta = datos["routes"][0] if datos else None
            if ruta:
                return Trayecto(
                    geometria=[(c[0], c[1]) for c in ruta["geometry"]["coordinates"]],
                    distancia_m=float(ruta["distance"]),
                    duracion_s=float(ruta["duration"]) * settings.RUTAS_FACTOR_TRAFICO,
                    estimado=False,
                )
        except (KeyError, IndexError, TypeError, ValueError) as error:
            logger.warning("Respuesta de OSRM inesperada: %s", error)
    km = sum(distancia_haversine_km(a, b) for a, b in zip(puntos, puntos[1:], strict=False)) * settings.RUTAS_FACTOR_DESVIO
    return Trayecto([], km * 1000, km / settings.RUTAS_VELOCIDAD_MEDIA_KMH * 3600, True)


async def calcular_matriz(puntos: list[tuple[float, float]]) -> list[list[float]] | None:
    """Segundos de manejo entre cada par de puntos (respetando sentidos de circulación)."""
    if not 2 <= len(puntos) <= MAX_PUNTOS:
        return None
    datos = await _consultar(f"table/v1/driving/{_coordenadas(puntos)}", {"annotations": "duration"})
    filas = datos.get("durations") if datos else None
    if not filas or len(filas) != len(puntos):
        return None
    # Un tramo sin camino (null) se penaliza para que el orden lo evite.
    return [[float(v) if v is not None else 10**7 for v in fila] for fila in filas]


class ServicioRutasOsrm:
    """Implementación de `IServicioRutas` con OSRM."""

    async def matriz(self, puntos: list[tuple[float, float]]) -> list[list[float]] | None:
        return await calcular_matriz(puntos)

    async def recorrido(self, puntos: list[tuple[float, float]]) -> tuple[float, float] | None:
        trayecto = await calcular_trayecto(puntos)
        return None if trayecto.estimado else (trayecto.distancia_m, trayecto.duracion_s)
