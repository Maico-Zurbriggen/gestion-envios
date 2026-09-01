import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.application.interfaces.repositorio_roles import IRepositorioRoles
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.application.interfaces.repositorio_usuarios import IRepositorioUsuarios
from app.application.interfaces.servicio_auth import IServicioAuth
from app.application.interfaces.servicio_empleados import IServicioEmpleados
from app.application.interfaces.servicio_envios import IServicioEnvios
from app.application.interfaces.servicio_seguimiento import IServicioSeguimiento
from app.application.interfaces.servicio_sucursales import IServicioSucursales
from app.application.services.servicio_auth import ServicioAuth
from app.application.services.servicio_empleados import ServicioEmpleados
from app.application.services.servicio_envios import ServicioEnvios
from app.application.services.servicio_seguimiento import ServicioSeguimiento
from app.application.services.servicio_sucursales import ServicioSucursales
from app.core.exceptions import (
    ForbiddenAccessException,
    ForbiddenScopeException,
    InvalidTokenException,
)
from app.domain.constants.roles import RolEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import UsuarioModel
from app.infrastructure.db.session import obtener_sesion_db
from app.infrastructure.repositories.repositorio_envios import RepositorioEnvios
from app.infrastructure.repositories.repositorio_roles import RepositorioRoles
from app.infrastructure.repositories.repositorio_sucursales import RepositorioSucursales
from app.infrastructure.repositories.repositorio_usuarios import RepositorioUsuarios

security_bearer = HTTPBearer(auto_error=False)


# --- Inyección de Repositorios y Servicios ---


def get_repositorio_usuarios(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioUsuarios:
    return RepositorioUsuarios(db)


def get_repositorio_roles(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioRoles:
    return RepositorioRoles(db)


def get_servicio_auth(
    repo_usuarios: IRepositorioUsuarios = Depends(get_repositorio_usuarios),
) -> IServicioAuth:
    return ServicioAuth(repositorio_usuarios=repo_usuarios)


def get_servicio_empleados(
    repo_usuarios: IRepositorioUsuarios = Depends(get_repositorio_usuarios),
    repo_roles: IRepositorioRoles = Depends(get_repositorio_roles),
) -> IServicioEmpleados:
    return ServicioEmpleados(
        repositorio_usuarios=repo_usuarios,
        repositorio_roles=repo_roles,
    )


def get_repositorio_envios(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioEnvios:
    return RepositorioEnvios(db)


def get_repositorio_sucursales(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioSucursales:
    return RepositorioSucursales(db)


def get_servicio_envios(
    repo_envios: IRepositorioEnvios = Depends(get_repositorio_envios),
    repo_sucursales: IRepositorioSucursales = Depends(get_repositorio_sucursales),
) -> IServicioEnvios:
    return ServicioEnvios(repositorio_envios=repo_envios, repositorio_sucursales=repo_sucursales)


def get_servicio_seguimiento(
    repo_envios: IRepositorioEnvios = Depends(get_repositorio_envios),
) -> IServicioSeguimiento:
    return ServicioSeguimiento(repositorio_envios=repo_envios)


def get_servicio_sucursales(
    repo_sucursales: IRepositorioSucursales = Depends(get_repositorio_sucursales),
) -> IServicioSucursales:
    return ServicioSucursales(repositorio_sucursales=repo_sucursales)


# --- Inyección de Autenticación y Autorización ---


async def obtener_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Dict[str, Any]:
    """Extrae y decodifica el token JWT del encabezado Authorization: Bearer."""
    if not credentials or not credentials.credentials:
        raise InvalidTokenException("Token de autenticación ausente o inválido.")
    return ManejadorJWT.decodificar_token(credentials.credentials)


async def obtener_usuario_actual(
    payload: Dict[str, Any] = Depends(obtener_token_payload),
    repo_usuarios: IRepositorioUsuarios = Depends(get_repositorio_usuarios),
) -> UsuarioModel:
    """Valida el token y recupera la entidad completa del usuario autenticado."""
    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise InvalidTokenException("El identificador del usuario en el token no es válido.")

    usuario = await repo_usuarios.obtener_por_id(user_id)
    if not usuario:
        raise InvalidTokenException("El usuario asociado al token no existe.")

    if usuario.estado != "Activo":
        raise ForbiddenAccessException("La cuenta de usuario se encuentra inactiva o bloqueada.")

    return usuario


def requerir_scope(scope_requerido: str) -> Callable:
    """Fabrica una dependencia que restringe el acceso al scope JWT especificado."""
    async def validador_scope(payload: Dict[str, Any] = Depends(obtener_token_payload)) -> Dict[str, Any]:
        scope_actual = payload.get("scope")
        if scope_actual != scope_requerido:
            raise ForbiddenScopeException(
                f"El token no posee el alcance necesario ({scope_requerido})."
            )
        return payload

    return validador_scope


async def validar_token_para_cambio_password(
    payload: Dict[str, Any] = Depends(obtener_token_payload),
) -> Dict[str, Any]:
    """Permite el acceso al endpoint de cambio de clave tanto con token temporal como con token pleno."""
    scope_actual = payload.get("scope")
    if scope_actual not in [
        ScopeEnum.PASSWORD_RESET_ONLY.value,
        ScopeEnum.FULL_ACCESS.value,
    ]:
        raise ForbiddenScopeException("Alcance de token no autorizado para cambio de clave.")
    return payload


def requerir_rol(rol_requerido: RolEnum) -> Callable:
    """Fabrica una dependencia que valida que el usuario posea un rol específico y acceso pleno."""
    async def validador_rol(
        payload: Dict[str, Any] = Depends(obtener_token_payload),
        repo_usuarios: IRepositorioUsuarios = Depends(get_repositorio_usuarios),
    ) -> UsuarioModel:
        # 1. Validar Scope primero: si tiene token restringido, denegar inmediatamente
        if payload.get("scope") == ScopeEnum.PASSWORD_RESET_ONLY.value:
            raise ForbiddenScopeException("Debe completar el cambio de contraseña antes de operar.")

        # 2. Validar Usuario existente
        try:
            user_id = uuid.UUID(payload.get("sub", ""))
        except (ValueError, TypeError):
            raise InvalidTokenException("El identificador del usuario en el token no es válido.")

        usuario = await repo_usuarios.obtener_por_id(user_id)
        if not usuario:
            raise InvalidTokenException("El usuario asociado al token no existe.")

        if usuario.estado != "Activo":
            raise ForbiddenAccessException("La cuenta de usuario se encuentra inactiva o bloqueada.")

        # 3. Validar Rol
        rol_actual = usuario.rol.nombre if usuario.rol else ""
        if rol_actual != rol_requerido.value:
            raise ForbiddenAccessException(
                f"Acceso denegado. Se requiere rol {rol_requerido.value}."
            )
        return usuario

    return validador_rol

