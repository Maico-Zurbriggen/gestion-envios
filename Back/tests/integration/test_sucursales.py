import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_listar_sucursales_publico(client: AsyncClient):
    """El catálogo de sucursales es público y no requiere autenticación."""
    resp = await client.get("/api/v1/sucursales")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 2
    sucursal = data["data"][0]
    for campo in ("id", "nombre", "provincia", "ciudad", "direccion", "latitud", "longitud"):
        assert campo in sucursal
