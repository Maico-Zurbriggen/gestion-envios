import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositorio_entregas import IRepositorioEntregas
from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.application.interfaces.repositorio_notificaciones import IRepositorioNotificaciones
from app.application.interfaces.repositorio_preguntas_frecuentes import IRepositorioPreguntasFrecuentes
from app.application.interfaces.repositorio_recepciones import IRepositorioRecepciones
from app.application.interfaces.repositorio_reclamos import IRepositorioReclamos
from app.application.interfaces.repositorio_recorridos import IRepositorioRecorridos
from app.application.interfaces.repositorio_repartidores import IRepositorioRepartidores
from app.application.interfaces.repositorio_roles import IRepositorioRoles
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.application.interfaces.repositorio_usuarios import IRepositorioUsuarios
from app.application.interfaces.servicio_auth import IServicioAuth
from app.application.interfaces.servicio_empleados import IServicioEmpleados
from app.application.interfaces.servicio_envios import IServicioEnvios
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.application.interfaces.servicio_preguntas_frecuentes import IServicioPreguntasFrecuentes
from app.application.interfaces.servicio_recepcion_terminal import IServicioRecepcionTerminal
from app.application.interfaces.servicio_reclamos import IServicioReclamos
from app.application.interfaces.servicio_recorridos import IServicioRecorridos
from app.application.interfaces.servicio_repartidores import IServicioRepartidores
from app.application.interfaces.servicio_reparto import IServicioReparto
from app.application.interfaces.servicio_retiro_sucursal import IServicioRetiroSucursal
from app.application.interfaces.servicio_roles import IServicioRoles
from app.application.interfaces.servicio_seguimiento import IServicioSeguimiento
from app.application.interfaces.servicio_sucursales import IServicioSucursales
from app.application.services.servicio_auth import ServicioAuth
from app.application.services.servicio_empleados import ServicioEmpleados
from app.application.services.servicio_envios import ServicioEnvios
from app.application.services.servicio_notificaciones import ServicioNotificaciones
from app.application.services.servicio_preguntas_frecuentes import ServicioPreguntasFrecuentes
from app.application.services.servicio_recepcion_terminal import ServicioRecepcionTerminal
from app.application.services.servicio_reclamos import ServicioReclamos
from app.application.services.servicio_recorridos import ServicioRecorridos
from app.application.services.servicio_repartidores import ServicioRepartidores
from app.application.services.servicio_reparto import ServicioReparto
from app.application.services.servicio_retiro_sucursal import ServicioRetiroSucursal
from app.application.services.servicio_roles import ServicioRoles
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
from app.infrastructure.db.session import AsyncSessionLocal, obtener_sesion_db
from app.infrastructure.email.email_provider import obtener_proveedor_email
from app.infrastructure.repositories.repositorio_entregas import RepositorioEntregas
from app.infrastructure.repositories.repositorio_envios import RepositorioEnvios
from app.infrastructure.repositories.repositorio_notificaciones import RepositorioNotificaciones
from app.infrastructure.repositories.repositorio_preguntas_frecuentes import RepositorioPreguntasFrecuentes
from app.infrastructure.repositories.repositorio_recepciones import RepositorioRecepciones
from app.infrastructure.repositories.repositorio_reclamos import RepositorioReclamos
from app.infrastructure.repositories.repositorio_recorridos import RepositorioRecorridos
from app.infrastructure.repositories.repositorio_repartidores import RepositorioRepartidores
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
    repo_envios: IRepositorioEnvios = Depends(get_repositorio_envios),
) -> IServicioSucursales:
    """Además del catálogo (HU03), el servicio resuelve las opciones de retiro de
    un envío por su token de seguimiento (HU09), por eso recibe ambos repositorios."""
    return ServicioSucursales(
        repositorio_sucursales=repo_sucursales,
        repositorio_envios=repo_envios,
    )


def get_servicio_roles(
    repo_roles: IRepositorioRoles = Depends(get_repositorio_roles),
) -> IServicioRoles:
    return ServicioRoles(repositorio_roles=repo_roles)


def get_repositorio_notificaciones(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioNotificaciones:
    return RepositorioNotificaciones(db)


def get_session_factory() -> Callable[[], AsyncSession]:
    """Provee la fábrica de sesiones asíncronas para tareas en segundo plano."""
    return AsyncSessionLocal


def get_servicio_notificaciones(
    session_factory: Callable[[], AsyncSession] = Depends(get_session_factory),
    repo_notificaciones: IRepositorioNotificaciones = Depends(get_repositorio_notificaciones),
) -> IServicioNotificaciones:
    return ServicioNotificaciones(
        email_provider=obtener_proveedor_email(),
        session_factory=session_factory,
        repo_notificaciones=repo_notificaciones,
    )


def get_repositorio_entregas(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioEntregas:
    return RepositorioEntregas(db)


def get_servicio_retiro_sucursal(
    repo_entregas: IRepositorioEntregas = Depends(get_repositorio_entregas),
) -> IServicioRetiroSucursal:
    return ServicioRetiroSucursal(repositorio_entregas=repo_entregas)


def get_repositorio_recepciones(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioRecepciones:
    return RepositorioRecepciones(db)


def get_servicio_recepcion_terminal(
    repo_recepciones: IRepositorioRecepciones = Depends(get_repositorio_recepciones),
    repo_sucursales: IRepositorioSucursales = Depends(get_repositorio_sucursales),
) -> IServicioRecepcionTerminal:
    """Recepción de paquetes en terminal (HU06). Necesita el catálogo de
    sucursales para validar la terminal donde se recibe el paquete."""
    return ServicioRecepcionTerminal(
        repositorio_recepciones=repo_recepciones,
        repositorio_sucursales=repo_sucursales,
    )


def get_repositorio_preguntas_frecuentes(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioPreguntasFrecuentes:
    return RepositorioPreguntasFrecuentes(db)


def get_servicio_preguntas_frecuentes(
    repo_preguntas: IRepositorioPreguntasFrecuentes = Depends(get_repositorio_preguntas_frecuentes),
) -> IServicioPreguntasFrecuentes:
    """Sección pública de preguntas frecuentes y administración de su contenido (HU08)."""
    return ServicioPreguntasFrecuentes(repositorio_preguntas=repo_preguntas)


def get_repositorio_reclamos(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioReclamos:
    return RepositorioReclamos(db)


def get_servicio_reclamos(
    repo_reclamos: IRepositorioReclamos = Depends(get_repositorio_reclamos),
    repo_envios: IRepositorioEnvios = Depends(get_repositorio_envios),
) -> IServicioReclamos:
    """Reclamos desde la vista pública del token (HU07). Resuelve el envío con
    el mismo repositorio que el seguimiento de HU04."""
    return ServicioReclamos(repositorio_reclamos=repo_reclamos, repositorio_envios=repo_envios)


def get_repositorio_repartidores(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioRepartidores:
    return RepositorioRepartidores(db)


def get_servicio_repartidores(
    repo_repartidores: IRepositorioRepartidores = Depends(get_repositorio_repartidores),
    repo_sucursales: IRepositorioSucursales = Depends(get_repositorio_sucursales),
) -> IServicioRepartidores:
    """Perfiles operativos de repartidor (sucursal base y tipo de reparto), soporte de HU10."""
    return ServicioRepartidores(repositorio_repartidores=repo_repartidores, repositorio_sucursales=repo_sucursales)


def get_repositorio_recorridos(
    db: AsyncSession = Depends(obtener_sesion_db),
) -> IRepositorioRecorridos:
    return RepositorioRecorridos(db)


def get_servicio_recorridos(
    repo_recorridos: IRepositorioRecorridos = Depends(get_repositorio_recorridos),
    repo_sucursales: IRepositorioSucursales = Depends(get_repositorio_sucursales),
) -> IServicioRecorridos:
    """Generación, visualización y edición de recorridos (HU10). Necesita el
    catálogo de sucursales para ubicar el origen y las paradas de larga distancia."""
    return ServicioRecorridos(repositorio_recorridos=repo_recorridos, repositorio_sucursales=repo_sucursales)


def get_servicio_reparto(
    repo_recorridos: IRepositorioRecorridos = Depends(get_repositorio_recorridos),
    repo_entregas: IRepositorioEntregas = Depends(get_repositorio_entregas),
    servicio_recorridos: IServicioRecorridos = Depends(get_servicio_recorridos),
) -> IServicioReparto:
    return ServicioReparto(repo_recorridos, repo_entregas, servicio_recorridos)


# --- Inyección de Autenticación y Autorización ---


async def obtener_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any]:
    """Extrae y decodifica el token JWT del encabezado Authorization: Bearer."""
    if not credentials or not credentials.credentials:
        raise InvalidTokenException("Token de autenticación ausente o inválido.")
    return ManejadorJWT.decodificar_token(credentials.credentials)


async def obtener_usuario_actual(
    payload: dict[str, Any] = Depends(obtener_token_payload),
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
    async def validador_scope(payload: dict[str, Any] = Depends(obtener_token_payload)) -> dict[str, Any]:
        scope_actual = payload.get("scope")
        if scope_actual != scope_requerido:
            raise ForbiddenScopeException(
                f"El token no posee el alcance necesario ({scope_requerido})."
            )
        return payload

    return validador_scope


async def validar_token_para_cambio_password(
    payload: dict[str, Any] = Depends(obtener_token_payload),
) -> dict[str, Any]:
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
        payload: dict[str, Any] = Depends(obtener_token_payload),
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


def requerir_roles(roles_permitidos: list[RolEnum]) -> Callable:
    """Fabrica una dependencia que valida que el usuario posea alguno de los roles indicados y acceso pleno."""
    async def validador_roles(
        payload: dict[str, Any] = Depends(obtener_token_payload),
        repo_usuarios: IRepositorioUsuarios = Depends(get_repositorio_usuarios),
    ) -> UsuarioModel:
        if payload.get("scope") == ScopeEnum.PASSWORD_RESET_ONLY.value:
            raise ForbiddenScopeException("Debe completar el cambio de contraseña antes de operar.")

        try:
            user_id = uuid.UUID(payload.get("sub", ""))
        except (ValueError, TypeError):
            raise InvalidTokenException("El identificador del usuario en el token no es válido.")

        usuario = await repo_usuarios.obtener_por_id(user_id)
        if not usuario:
            raise InvalidTokenException("El usuario asociado al token no existe.")

        if usuario.estado != "Activo":
            raise ForbiddenAccessException("La cuenta de usuario se encuentra inactiva o bloqueada.")

        rol_actual = usuario.rol.nombre if usuario.rol else ""
        nombres_permitidos = [r.value for r in roles_permitidos]
        if rol_actual not in nombres_permitidos:
            raise ForbiddenAccessException(
                f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(nombres_permitidos)}."
            )
        return usuario

    return validador_roles

