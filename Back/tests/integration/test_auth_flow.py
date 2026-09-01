import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.roles import RolIdEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import UsuarioModel


@pytest.mark.asyncio
async def test_hu01_escenario_1_login_superadmin_exitoso(client: AsyncClient):
    """HU01 - Escenario 1: Inicio de sesión exitoso del Superadministrador con credenciales precargadas."""
    payload = {
        "dni": settings.SUPERADMIN_SEED_DNI,
        "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "token" in data["data"]
    assert data["data"]["user"]["dni"] == settings.SUPERADMIN_SEED_DNI
    assert data["data"]["user"]["rol"] == "SUPERADMIN"
    assert data["data"]["user"]["requiere_cambio_password"] is False


@pytest.mark.asyncio
async def test_hu01_escenario_2_login_credenciales_incorrectas(client: AsyncClient):
    """HU01 - Escenario 2: Rechazo de autenticación con credenciales incorrectas."""
    # Contraseña incorrecta
    payload_pass_mal = {
        "dni": settings.SUPERADMIN_SEED_DNI,
        "password": "PasswordTotalmenteErronea123!",
    }
    resp = await client.post("/api/v1/auth/login", json=payload_pass_mal)
    assert resp.status_code == 401
    err = resp.json()
    assert err["status"] == "error"
    assert err["code"] == ErrorCodes.AUTH_FAILED
    assert err["message"] == "Credenciales inválidas."

    # DNI no registrado
    payload_dni_inexistente = {
        "dni": "99999999",
        "password": "CualquierPassword123!",
    }
    resp2 = await client.post("/api/v1/auth/login", json=payload_dni_inexistente)
    assert resp2.status_code == 401
    assert resp2.json()["code"] == ErrorCodes.AUTH_FAILED


@pytest.mark.asyncio
async def test_hu02_flujo_completo_primer_acceso_y_cambio_password(
    client: AsyncClient, db_session: AsyncSession
):
    """HU02 - Escenarios 1, 2, 3 y 4: Flujo completo de primer acceso de empleado administrativo."""
    # 1. Crear usuario administrativo con contraseña temporal
    temp_password = "Tmp#9284Kz1!"
    dni_empleado = "38123456"
    usuario = UsuarioModel(
        nombre="Laura Martínez",
        dni=dni_empleado,
        email="laura.martinez@empresa.com",
        telefono="+543564998877",
        password_hash=HasherContrasenas.generar_hash(temp_password),
        estado="Activo",
        requiere_cambio_password=True,
        rol_id=RolIdEnum.ADMINISTRATIVO.value,
    )
    db_session.add(usuario)
    await db_session.commit()

    # --- Escenario 1: Primer acceso válido detecta requiere_cambio_password=True ---
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"dni": dni_empleado, "password": temp_password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["status"] == "requires_password_change"
    assert login_data["message"] == "Debe cambiar su contraseña temporal antes de continuar."
    assert login_data["data"]["requiere_cambio_password"] is True
    temp_token = login_data["data"]["temp_token"]
    assert temp_token is not None

    headers_temp = {"Authorization": f"Bearer {temp_token}"}

    # --- Escenario 3: Intento de cambio con confirmación que no coincide ---
    resp_no_match = await client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers_temp,
        json={
            "password_actual": temp_password,
            "nueva_password": "MiNuevaPasswordSegura2026!",
            "confirmacion_password": "PasswordQueNoCoincide2026!",
        },
    )
    assert resp_no_match.status_code == 400
    data_no_match = resp_no_match.json()
    assert data_no_match["code"] == ErrorCodes.PASSWORD_POLICY_ERROR

    # --- Escenario 3: Intento de cambio con contraseña débil (< 10 caracteres o sin símbolos) ---
    resp_debil = await client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers_temp,
        json={
            "password_actual": temp_password,
            "nueva_password": "corta1!",
            "confirmacion_password": "corta1!",
        },
    )
    assert resp_debil.status_code == 400
    assert resp_debil.json()["code"] == ErrorCodes.PASSWORD_POLICY_ERROR

    # --- Escenario 3: Intento de cambio con contraseña actual errónea ---
    resp_actual_erronea = await client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers_temp,
        json={
            "password_actual": "PasswordActualEquivocada!",
            "nueva_password": "MiNuevaPasswordSegura2026!",
            "confirmacion_password": "MiNuevaPasswordSegura2026!",
        },
    )
    assert resp_actual_erronea.status_code == 400
    assert resp_actual_erronea.json()["code"] == ErrorCodes.PASSWORD_POLICY_ERROR

    # --- Escenario 2: Cambio de contraseña exitoso ---
    nueva_clave = "MiNuevaPasswordSegura2026!"
    resp_cambio_ok = await client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers_temp,
        json={
            "password_actual": temp_password,
            "nueva_password": nueva_clave,
            "confirmacion_password": nueva_clave,
        },
    )
    assert resp_cambio_ok.status_code == 200
    data_cambio_ok = resp_cambio_ok.json()
    assert data_cambio_ok["status"] == "success"
    assert "auth_token" in data_cambio_ok["data"]

    # --- Escenario 4: Accesos posteriores con la nueva contraseña ---
    login_posterior = await client.post(
        "/api/v1/auth/login",
        json={"dni": dni_empleado, "password": nueva_clave},
    )
    assert login_posterior.status_code == 200
    data_posterior = login_posterior.json()
    assert data_posterior["status"] == "success"
    assert data_posterior["data"]["user"]["requiere_cambio_password"] is False
    assert data_posterior["data"]["user"]["email"] == "laura.martinez@empresa.com"

    # La clave temporal anterior ya no debe funcionar
    login_clave_vieja = await client.post(
        "/api/v1/auth/login",
        json={"dni": dni_empleado, "password": temp_password},
    )
    assert login_clave_vieja.status_code == 401
    assert login_clave_vieja.json()["code"] == ErrorCodes.AUTH_FAILED


@pytest.mark.asyncio
async def test_login_con_token_y_endpoint_me(client: AsyncClient, db_session: AsyncSession):
    """Verifica el login mediante token JWT y la consulta de perfil /me."""
    # 1. Login inicial de superadmin para obtener token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "dni": settings.SUPERADMIN_SEED_DNI,
            "password": settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*",
        },
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["token"]

    # 2. Login con token enviándolo en el body JSON
    resp_token_body = await client.post(
        "/api/v1/auth/login-token",
        json={"token": token},
    )
    assert resp_token_body.status_code == 200
    data_token_body = resp_token_body.json()
    assert data_token_body["status"] == "success"
    assert data_token_body["data"]["user"]["dni"] == settings.SUPERADMIN_SEED_DNI
    assert data_token_body["data"]["user"]["rol"] == "SUPERADMIN"

    # 3. Login con token enviándolo en el header Authorization Bearer
    resp_token_header = await client.post(
        "/api/v1/auth/login-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_token_header.status_code == 200
    assert resp_token_header.json()["status"] == "success"

    # 4. Consulta a /api/v1/auth/me
    resp_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_me.status_code == 200
    data_me = resp_me.json()
    assert data_me["status"] == "success"
    assert data_me["data"]["user"]["dni"] == settings.SUPERADMIN_SEED_DNI

    # 5. Error al invocar login-token sin token
    resp_sin_token = await client.post("/api/v1/auth/login-token", json={})
    assert resp_sin_token.status_code == 401
    assert resp_sin_token.json()["code"] == ErrorCodes.INVALID_TOKEN


