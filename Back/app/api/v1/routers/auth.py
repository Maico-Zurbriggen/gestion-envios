import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_servicio_auth,
    obtener_usuario_actual,
    security_bearer,
    validar_token_para_cambio_password,
)
from app.application.interfaces.servicio_auth import IServicioAuth
from app.contracts.auth import (
    CambiarPasswordRequest,
    CambiarPasswordResponse,
    LoginRequest,
    LoginResponseUnion,
    LoginSuccessResponse,
    LoginTokenRequest,
)
from app.core.exceptions import InvalidTokenException
from app.infrastructure.db.models import UsuarioModel

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
    "/login-token",
    response_model=LoginResponseUnion,
    status_code=status.HTTP_200_OK,
    summary="Inicio de sesión o validación mediante Token JWT",
    description="Autentica o reanuda la sesión a partir de un token JWT generado previamente. Soporta token en el body JSON o en la cabecera Authorization: Bearer.",
)
async def login_token(
    datos: Optional[LoginTokenRequest] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    servicio_auth: IServicioAuth = Depends(get_servicio_auth),
):
    """Endpoint para iniciar sesión o validar acceso con token (primer acceso o accesos posteriores)."""
    token_str = (datos.token if datos and datos.token else None) or (
        credentials.credentials if credentials and credentials.credentials else None
    )

    if not token_str:
        raise InvalidTokenException("Token de autenticación no proporcionado.")

    return await servicio_auth.autenticar_con_token(token=token_str)


@router.get(
    "/me",
    response_model=LoginSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener información del usuario autenticado",
    description="Valida el token Bearer en el encabezado Authorization y retorna la información completa del usuario actual.",
)
async def me(
    usuario_actual: UsuarioModel = Depends(obtener_usuario_actual),
    servicio_auth: IServicioAuth = Depends(get_servicio_auth),
):
    """Endpoint para consultar la sesión y perfil del usuario autenticado."""
    return await servicio_auth.obtener_usuario_por_id(usuario_actual.id)


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


