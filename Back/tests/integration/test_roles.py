import pytest
from httpx import AsyncClient

from app.domain.constants.roles import RolEnum, RolIdEnum


@pytest.mark.asyncio
async def test_listar_roles_exitoso(client: AsyncClient):
    """Verifica que el endpoint GET /api/v1/roles retorne todos los roles con sus IDs numéricos."""
    response = await client.get("/api/v1/roles")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data

    roles = data["data"]
    assert len(roles) >= 4

    roles_map = {r["nombre"]: r["id"] for r in roles}

    assert roles_map[RolEnum.SUPERADMIN.value] == RolIdEnum.SUPERADMIN.value
    assert roles_map[RolEnum.ADMINISTRATIVO.value] == RolIdEnum.ADMINISTRATIVO.value
    assert roles_map[RolEnum.VENDEDOR.value] == RolIdEnum.VENDEDOR.value
    assert roles_map[RolEnum.REPARTIDOR.value] == RolIdEnum.REPARTIDOR.value

    # Verificar que cada objeto contenga id, nombre y descripcion
    for rol in roles:
        assert "id" in rol
        assert "nombre" in rol
        assert "descripcion" in rol
        assert isinstance(rol["id"], int)
        assert isinstance(rol["nombre"], str)

