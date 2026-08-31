import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import UsuarioModel


@pytest.mark.asyncio
async def test_acceso_denegado_con_scope_password_reset_only(
    client: AsyncClient,
):
    """Verifica que un token con scope PASSWORD_RESET_ONLY no pueda acceder a endpoints administrativos."""
    temp_token = ManejadorJWT.emitir_token(
        usuario_id="00000000-0000-0000-0000-000000000002",
        rol=RolEnum.SUPERADMIN.value,
        scope=ScopeEnum.PASSWORD_RESET_ONLY.value,
    )
    headers = {"Authorization": f"Bearer {temp_token}"}

    payload = {
        "nombre": "Prueba",
        "dni": "40111222",
        "email": "prueba@empresa.com",
        "telefono": "+543564123456",
        "rol_id": 2,
    }
    resp = await client.post("/api/v1/admin/empleados", json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCodes.FORBIDDEN_SCOPE


@pytest.mark.asyncio
async def test_acceso_denegado_para_rol_no_superadmin(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifica que un usuario con rol ADMINISTRATIVO no pueda dar de alta empleados."""
    admin_user = UsuarioModel(
        nombre="Admin Operativo",
        dni="22333444",
        email="operativo@empresa.com",
        telefono="+543564111222",
        password_hash=HasherContrasenas.generar_hash("Password123!*"),
        estado="Activo",
        requiere_cambio_password=False,
        rol_id=RolIdEnum.ADMINISTRATIVO.value,
    )
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)

    admin_token = ManejadorJWT.emitir_token(
        usuario_id=str(admin_user.id),
        rol=RolEnum.ADMINISTRATIVO.value,
        scope=ScopeEnum.FULL_ACCESS.value,
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "nombre": "Prueba",
        "dni": "40111222",
        "email": "prueba@empresa.com",
        "telefono": "+543564123456",
        "rol_id": 2,
    }
    resp = await client.post("/api/v1/admin/empleados", json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS


@pytest.mark.asyncio
async def test_acceso_sin_token_rechazado(
    client: AsyncClient,
):
    """Verifica que solicitudes no autenticadas devuelvan 401 INVALID_TOKEN."""
    resp = await client.post("/api/v1/admin/empleados", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == ErrorCodes.INVALID_TOKEN

