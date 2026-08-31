import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT


@pytest.mark.asyncio
async def test_hu01_escenario_3_alta_empleado_exitosa(
    client: AsyncClient,
):
    """HU01 - Escenario 3: Alta de empleado válida por Superadministrador."""
    # 1. Login como Superadmin para obtener token real
    login_super = await client.post(
        "/api/v1/auth/login",
        json={
            "dni": settings.SUPERADMIN_SEED_DNI,
            "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*",
        },
    )
    token_super = login_super.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token_super}"}

    payload_empleado = {
        "nombre": "Carlos Gómez",
        "dni": "35123456",
        "email": "carlos.gomez@empresa.com",
        "telefono": "+543564123456",
        "rol_id": RolIdEnum.ADMINISTRATIVO.value,
    }

    resp = await client.post("/api/v1/admin/empleados", json=payload_empleado, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Empleado creado correctamente."
    emp = data["data"]
    assert emp["nombre"] == "Carlos Gómez"
    assert emp["dni"] == "35123456"
    assert emp["email"] == "carlos.gomez@empresa.com"
    assert emp["estado"] == "Activo"
    assert emp["rol"] == "ADMINISTRATIVO"
    assert "password_temporal" in emp
    assert len(emp["password_temporal"]) >= 10

    # Verificar que el nuevo empleado pueda loguearse inmediatamente con su clave temporal
    login_nuevo = await client.post(
        "/api/v1/auth/login",
        json={"dni": "35123456", "password": emp["password_temporal"]},
    )
    assert login_nuevo.status_code == 200
    assert login_nuevo.json()["status"] == "requires_password_change"


@pytest.mark.asyncio
async def test_hu01_escenario_4_alta_empleado_duplicado(
    client: AsyncClient,
):
    """HU01 - Escenario 4: Rechazo por DNI o Email duplicado."""
    login_super = await client.post(
        "/api/v1/auth/login",
        json={
            "dni": settings.SUPERADMIN_SEED_DNI,
            "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*",
        },
    )
    headers = {"Authorization": f"Bearer {login_super.json()['data']['token']}"}

    payload = {
        "nombre": "Mariano López",
        "dni": "36111222",
        "email": "mariano.lopez@empresa.com",
        "telefono": "+543564112233",
        "rol_id": RolIdEnum.ADMINISTRATIVO.value,
    }
    # Crear por primera vez
    resp1 = await client.post("/api/v1/admin/empleados", json=payload, headers=headers)
    assert resp1.status_code == 201

    # Intentar duplicar DNI
    payload_mismo_dni = {
        "nombre": "Otro Nombre",
        "dni": "36111222",
        "email": "otro.email@empresa.com",
        "telefono": "+543564000000",
        "rol_id": RolIdEnum.ADMINISTRATIVO.value,
    }
    resp_dup_dni = await client.post("/api/v1/admin/empleados", json=payload_mismo_dni, headers=headers)
    assert resp_dup_dni.status_code == 409
    assert resp_dup_dni.json()["code"] == ErrorCodes.DUPLICATE_ENTRY

    # Intentar duplicar Email
    payload_mismo_email = {
        "nombre": "Otro Nombre",
        "dni": "37999888",
        "email": "mariano.lopez@empresa.com",
        "telefono": "+543564000000",
        "rol_id": RolIdEnum.ADMINISTRATIVO.value,
    }
    resp_dup_email = await client.post("/api/v1/admin/empleados", json=payload_mismo_email, headers=headers)
    assert resp_dup_email.status_code == 409
    assert resp_dup_email.json()["code"] == ErrorCodes.DUPLICATE_ENTRY


@pytest.mark.asyncio
async def test_hu01_escenario_4_alta_empleado_datos_invalidos(
    client: AsyncClient,
):
    """HU01 - Escenario 4: Rechazo con código 400 por payload formalmente inválido."""
    login_super = await client.post(
        "/api/v1/auth/login",
        json={
            "dni": settings.SUPERADMIN_SEED_DNI,
            "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*",
        },
    )
    headers = {"Authorization": f"Bearer {login_super.json()['data']['token']}"}

    # DNI con letras
    payload_dni_invalido = {
        "nombre": "Pedro Ruiz",
        "dni": "35A23456",
        "email": "pedro.ruiz@empresa.com",
        "telefono": "+543564123456",
        "rol_id": 2,
    }
    resp = await client.post("/api/v1/admin/empleados", json=payload_dni_invalido, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR

    # Email inválido
    payload_email_invalido = {
        "nombre": "Pedro Ruiz",
        "dni": "35123456",
        "email": "pedro-sin-arroba-ni-dominio",
        "telefono": "+543564123456",
        "rol_id": 2,
    }
    resp2 = await client.post("/api/v1/admin/empleados", json=payload_email_invalido, headers=headers)
    assert resp2.status_code == 400
    assert resp2.json()["code"] == ErrorCodes.VALIDATION_ERROR

