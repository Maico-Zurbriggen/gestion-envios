"""Mapa: recorrido por calles (OSRM) y ubicación de direcciones (Georef + Nominatim)."""

import pytest
from httpx import AsyncClient

from app.api.v1.routers import mapas
from app.core.config import settings
from app.infrastructure.mapas.ubicacion import Ubicacion

pytestmark = pytest.mark.asyncio

CORDOBA = [{"latitud": -31.4167, "longitud": -64.1833}, {"latitud": -31.4241, "longitud": -64.1872}]


async def test_trayecto_sin_osrm_se_estima_en_linea_recta(client: AsyncClient, administrativo_token: str, monkeypatch):
    monkeypatch.setattr(settings, "OSRM_URL", "")
    resp = await client.post("/api/v1/mapa/trayecto", headers={"Authorization": f"Bearer {administrativo_token}"}, json={"puntos": CORDOBA})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["estimado"] is True
    assert data["geometria"] == [], "sin cálculo por calles no se dibujan diagonales"
    assert 900 < data["distancia_m"] < 1500 and data["duracion_s"] > 0


async def test_trayecto_requiere_sesion(client: AsyncClient):
    assert (await client.post("/api/v1/mapa/trayecto", json={"puntos": CORDOBA})).status_code == 401


async def test_ubicar_direccion_es_publica(client: AsyncClient, monkeypatch):
    async def falsa(calle, altura, ciudad, provincia):
        assert (calle, altura, ciudad) == ("Av. Colón", "1234", "Córdoba")
        return Ubicacion(-31.40869, -64.19985, "AV COLON 1234, Capital, Córdoba", "direccion", "Georef")

    monkeypatch.setattr(mapas, "ubicar_direccion", falsa)
    resp = await client.get("/api/v1/mapa/ubicar", params={"calle": "Av. Colón", "altura": "1234", "ciudad": "Córdoba", "provincia": "Córdoba"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["precision"] == "direccion"


async def test_ubicar_sin_resultado_responde_404(client: AsyncClient, monkeypatch):
    async def nada(*_):
        return None

    monkeypatch.setattr(mapas, "ubicar_direccion", nada)
    resp = await client.get("/api/v1/mapa/ubicar", params={"ciudad": "Ciudad Inventada"})
    assert resp.status_code == 404
