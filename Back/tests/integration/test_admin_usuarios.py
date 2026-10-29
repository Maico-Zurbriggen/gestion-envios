"""Gestión de usuarios del personal: listado, edición, baja y blanqueo de contraseña."""

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.domain.constants.roles import RolIdEnum


async def _login_super(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"dni": settings.SUPERADMIN_SEED_DNI, "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*"},
    )
    body = resp.json()["data"]
    return {"headers": {"Authorization": f"Bearer {body['token']}"}, "id": body["user"]["id"]}


async def _crear(client: AsyncClient, headers: dict, dni: str, email: str, rol_id: int = RolIdEnum.ADMINISTRATIVO.value) -> dict:
    resp = await client.post(
        "/api/v1/admin/empleados",
        json={"nombre": "Laura Díaz", "dni": dni, "email": email, "telefono": "+543564123456", "rol_id": rol_id, "sucursal_ids": [1]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_listado_con_filtros_y_resumen(client: AsyncClient):
    sesion = await _login_super(client)
    await _crear(client, sesion["headers"], "30111222", "laura@empresa.com")
    await _crear(client, sesion["headers"], "30111333", "pedro@empresa.com", RolIdEnum.REPARTIDOR.value)

    resp = await client.get("/api/v1/admin/empleados", headers=sesion["headers"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 3
    assert data["resumen"] == {"total": 3, "activos": 3, "inactivos": 0, "por_rol": {"SUPERADMIN": 1, "ADMINISTRATIVO": 1, "REPARTIDOR": 1}}
    assert all(not ({"password_hash", "password_temporal"} & e.keys()) for e in data["empleados"])

    filtrado = await client.get("/api/v1/admin/empleados", params={"buscar": "PEDRO"}, headers=sesion["headers"])
    assert [e["email"] for e in filtrado.json()["data"]["empleados"]] == ["pedro@empresa.com"]
    assert filtrado.json()["data"]["resumen"]["total"] == 3, "el resumen no depende del filtro"

    por_rol = await client.get("/api/v1/admin/empleados", params={"rol_id": RolIdEnum.REPARTIDOR.value}, headers=sesion["headers"])
    assert [e["rol"] for e in por_rol.json()["data"]["empleados"]] == ["REPARTIDOR"]


@pytest.mark.asyncio
async def test_edicion_parcial_y_duplicados(client: AsyncClient):
    sesion = await _login_super(client)
    laura = await _crear(client, sesion["headers"], "30111222", "laura@empresa.com")
    await _crear(client, sesion["headers"], "30111333", "pedro@empresa.com")

    resp = await client.patch(
        f"/api/v1/admin/empleados/{laura['id']}",
        json={"nombre": "  Laura B. Díaz ", "email": "LAURA.DIAZ@empresa.com", "rol_id": RolIdEnum.VENDEDOR.value},
        headers=sesion["headers"],
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert (data["nombre"], data["email"], data["rol"], data["dni"]) == ("Laura B. Díaz", "laura.diaz@empresa.com", "VENDEDOR", "30111222")

    duplicado = await client.patch(f"/api/v1/admin/empleados/{laura['id']}", json={"email": "pedro@empresa.com"}, headers=sesion["headers"])
    assert duplicado.status_code == 409
    assert duplicado.json()["errors"][0]["field"] == "email"

    vacio = await client.patch(f"/api/v1/admin/empleados/{laura['id']}", json={}, headers=sesion["headers"])
    assert vacio.status_code == 400

    inexistente = await client.patch("/api/v1/admin/empleados/00000000-0000-0000-0000-000000000000", json={"nombre": "Otro"}, headers=sesion["headers"])
    assert inexistente.status_code == 404


@pytest.mark.asyncio
async def test_baja_bloquea_el_ingreso_y_reactivacion(client: AsyncClient):
    sesion = await _login_super(client)
    laura = await _crear(client, sesion["headers"], "30111222", "laura@empresa.com")

    baja = await client.patch(f"/api/v1/admin/empleados/{laura['id']}/estado", json={"estado": "Inactivo"}, headers=sesion["headers"])
    assert baja.status_code == 200
    assert baja.json()["data"]["estado"] == "Inactivo"
    login = await client.post("/api/v1/auth/login", json={"dni": "30111222", "password": laura["password_temporal"]})
    assert login.status_code in (401, 403)

    alta = await client.patch(f"/api/v1/admin/empleados/{laura['id']}/estado", json={"estado": "Activo"}, headers=sesion["headers"])
    assert alta.json()["data"]["estado"] == "Activo"
    login = await client.post("/api/v1/auth/login", json={"dni": "30111222", "password": laura["password_temporal"]})
    assert login.status_code == 200

    invalido = await client.patch(f"/api/v1/admin/empleados/{laura['id']}/estado", json={"estado": "Borrado"}, headers=sesion["headers"])
    assert invalido.status_code == 400


@pytest.mark.asyncio
async def test_nadie_se_quita_el_acceso_y_siempre_queda_un_superadmin(client: AsyncClient):
    sesion = await _login_super(client)
    yo = sesion["id"]

    propio_rol = await client.patch(f"/api/v1/admin/empleados/{yo}", json={"rol_id": RolIdEnum.ADMINISTRATIVO.value}, headers=sesion["headers"])
    assert propio_rol.status_code == 400
    propia_baja = await client.patch(f"/api/v1/admin/empleados/{yo}/estado", json={"estado": "Inactivo"}, headers=sesion["headers"])
    assert propia_baja.status_code == 400
    propio_blanqueo = await client.post(f"/api/v1/admin/empleados/{yo}/restablecer-password", headers=sesion["headers"])
    assert propio_blanqueo.status_code == 400
    propios_datos = await client.patch(f"/api/v1/admin/empleados/{yo}", json={"telefono": "+54 351 7654321"}, headers=sesion["headers"])
    assert propios_datos.status_code == 200, "sus propios datos de contacto sí puede editarlos"

    # Con un segundo superadmin, ese otro sí puede pasar a otro rol; quitar al último no.
    otro = await _crear(client, sesion["headers"], "30111444", "otro.super@empresa.com", RolIdEnum.SUPERADMIN.value)
    # Como administrativo tiene que pertenecer a alguna sucursal.
    sin_sucursal = await client.patch(f"/api/v1/admin/empleados/{otro['id']}", json={"rol_id": RolIdEnum.ADMINISTRATIVO.value}, headers=sesion["headers"])
    assert sin_sucursal.status_code == 400
    resp = await client.patch(
        f"/api/v1/admin/empleados/{otro['id']}", json={"rol_id": RolIdEnum.ADMINISTRATIVO.value, "sucursal_ids": [1]}, headers=sesion["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_blanqueo_exige_cambio_de_contrasena(client: AsyncClient):
    sesion = await _login_super(client)
    laura = await _crear(client, sesion["headers"], "30111222", "laura@empresa.com")

    resp = await client.post(f"/api/v1/admin/empleados/{laura['id']}/restablecer-password", headers=sesion["headers"])
    assert resp.status_code == 200
    nueva = resp.json()["data"]["password_temporal"]
    assert nueva != laura["password_temporal"] and len(nueva) >= 10

    vieja = await client.post("/api/v1/auth/login", json={"dni": "30111222", "password": laura["password_temporal"]})
    assert vieja.status_code == 401
    login = await client.post("/api/v1/auth/login", json={"dni": "30111222", "password": nueva})
    assert login.json()["status"] == "requires_password_change"


@pytest.mark.asyncio
async def test_solo_el_superadmin_gestiona_usuarios(client: AsyncClient, administrativo_token: str):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    assert (await client.get("/api/v1/admin/empleados", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/empleados")).status_code == 401
