import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    get_servicio_auth,
    validar_token_para_cambio_password,
)
from app.application.interfaces.servicio_auth import IServicioAuth
from app.contracts.auth import (
    CambiarPasswordRequest,
    CambiarPasswordResponse,
    LoginRequest,
    LoginResponseUnion,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=LoginResponseUnion,
    status_code=status.HTTP_200_OK,
    summary="Inicio de sesión de usuarios y superadministrador",
    description="Autentica credenciales (DNI y contraseña). Si el usuario requiere cambio de clave, devuelve un token temporal restringido.",
)
async def login(
    datos: LoginRequest,
    servicio_auth: IServicioAuth = Depends(get_servicio_auth),
):
    """Endpoint de Login unificado (HU01 y HU02)."""
    return await servicio_auth.autenticar_usuario(
        dni=datos.dni,
        password_plana=datos.password,
    )


@router.post(
    "/cambiar-password",
    response_model=CambiarPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambio obligatorio de contraseña",
    description="Permite al usuario cambiar su contraseña actual/temporal por una nueva que cumpla con la política de seguridad unificada.",
)
async def cambiar_password(
    datos: CambiarPasswordRequest,
    token_payload: Dict[str, Any] = Depends(validar_token_para_cambio_password),
    servicio_auth: IServicioAuth = Depends(get_servicio_auth),
):
    """Endpoint de cambio de contraseña (HU02)."""
    usuario_id = uuid.UUID(token_payload["sub"])
    return await servicio_auth.cambiar_password(
        usuario_id=usuario_id,
        password_actual=datos.password_actual,
        nueva_password=datos.nueva_password,
        confirmacion_password=datos.confirmacion_password,
    )

