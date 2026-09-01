from typing import Union
from uuid import UUID

from app.application.interfaces.repositorio_usuarios import IRepositorioUsuarios
from app.contracts.auth import (
    CambiarPasswordData,
    CambiarPasswordResponse,
    LoginNormalData,
    LoginRequiresPasswordChangeResponse,
    LoginSuccessResponse,
    LoginTempTokenData,
    UserInfoResponse,
)
from app.core.exceptions import (
    AuthFailedException,
    InvalidTokenException,
    PasswordPolicyException,
)
from app.domain.constants.scopes import ScopeEnum
from app.domain.rules.password_rules import validar_politica_password
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.auth.jwt_handler import ManejadorJWT


class ServicioAuth:
    """Servicio que implementa los casos de uso de Autenticación (HU01 y HU02)."""

    def __init__(
        self,
        repositorio_usuarios: IRepositorioUsuarios,
        hasher: HasherContrasenas = HasherContrasenas(),
        jwt_handler: ManejadorJWT = ManejadorJWT(),
    ):
        self.repo_usuarios = repositorio_usuarios
        self.hasher = hasher
        self.jwt_handler = jwt_handler

    async def autenticar_usuario(
        self, dni: str, password_plana: str
    ) -> Union[LoginSuccessResponse, LoginRequiresPasswordChangeResponse]:
        """Autentica a un usuario por su DNI y contraseña (Escenarios 1 y 2 de HU01, Escenario 1 y 4 de HU02)."""
        usuario = await self.repo_usuarios.obtener_por_dni(dni)
        if not usuario:
            raise AuthFailedException("Credenciales inválidas.")

        if not self.hasher.verificar_password(password_plana, usuario.password_hash):
            raise AuthFailedException("Credenciales inválidas.")

        if usuario.estado != "Activo":
            raise AuthFailedException("El usuario se encuentra inactivo o bloqueado.")

        rol_nombre = usuario.rol.nombre if usuario.rol else "ADMINISTRATIVO"

        # Flujo de Primer Acceso (HU02 - Escenario 1)
        if usuario.requiere_cambio_password:
            temp_token = self.jwt_handler.emitir_token(
                usuario_id=str(usuario.id),
                rol=rol_nombre,
                scope=ScopeEnum.PASSWORD_RESET_ONLY.value,
            )
            return LoginRequiresPasswordChangeResponse(
                status="requires_password_change",
                message="Debe cambiar su contraseña temporal antes de continuar.",
                data=LoginTempTokenData(
                    temp_token=temp_token,
                    requiere_cambio_password=True,
                ),
            )

        # Flujo de Login Normal (HU01 - Escenario 1 / HU02 - Escenario 4)
        token = self.jwt_handler.emitir_token(
            usuario_id=str(usuario.id),
            rol=rol_nombre,
            scope=ScopeEnum.FULL_ACCESS.value,
        )
        return LoginSuccessResponse(
            status="success",
            data=LoginNormalData(
                token=token,
                user=UserInfoResponse(
                    id=usuario.id,
                    nombre=usuario.nombre,
                    dni=usuario.dni,
                    email=usuario.email,
                    rol=rol_nombre,
                    requiere_cambio_password=False,
                ),
            ),
        )

    async def cambiar_password(
        self,
        usuario_id: UUID,
        password_actual: str,
        nueva_password: str,
        confirmacion_password: str,
    ) -> CambiarPasswordResponse:
        """Realiza el cambio obligatorio de contraseña (HU02 - Escenarios 2 y 3)."""
        # 1. Validar coincidencia de nueva contraseña y confirmación
        if nueva_password != confirmacion_password:
            raise PasswordPolicyException(
                message="Las contraseñas no coinciden o no cumplen con los requisitos de seguridad.",
                errors=[
                    {
                        "field": "confirmacion_password",
                        "message": "La confirmación de contraseña no coincide con la nueva contraseña.",
                    }
                ],
            )

        # 2. Validar política de seguridad de la nueva contraseña
        valida, error_msg = validar_politica_password(nueva_password)
        if not valida:
            raise PasswordPolicyException(
                message="Las contraseñas no coinciden o no cumplen con los requisitos de seguridad.",
                errors=[
                    {
                        "field": "nueva_password",
                        "message": error_msg or "La contraseña no cumple con la política de seguridad.",
                    }
                ],
            )

        # 3. Obtener usuario y verificar contraseña actual
        usuario = await self.repo_usuarios.obtener_por_id(usuario_id)
        if not usuario:
            raise InvalidTokenException("Usuario no encontrado.")

        if not self.hasher.verificar_password(password_actual, usuario.password_hash):
            raise PasswordPolicyException(
                message="La contraseña actual no es correcta.",
                errors=[
                    {
                        "field": "password_actual",
                        "message": "La contraseña actual ingresada es incorrecta.",
                    }
                ],
            )

        # 4. Generar nuevo hash y actualizar en BD
        nuevo_hash = self.hasher.generar_hash(nueva_password)
        await self.repo_usuarios.actualizar_password(usuario_id, nuevo_hash)

        # 5. Emitir nuevo JWT con permisos operativos plenos (FULL_ACCESS)
        rol_nombre = usuario.rol.nombre if usuario.rol else "ADMINISTRATIVO"
        auth_token = self.jwt_handler.emitir_token(
            usuario_id=str(usuario.id),
            rol=rol_nombre,
            scope=ScopeEnum.FULL_ACCESS.value,
        )

        return CambiarPasswordResponse(
            status="success",
            message="Contraseña actualizada exitosamente. Ya puede operar normalmente.",
            data=CambiarPasswordData(auth_token=auth_token),
        )

    async def autenticar_con_token(
        self, token: str
    ) -> Union[LoginSuccessResponse, LoginRequiresPasswordChangeResponse]:
        """Inicia sesión o valida la sesión utilizando un token JWT previamente emitido."""
        if not token or not token.strip():
            raise InvalidTokenException("Token de autenticación no proporcionado.")

        payload = self.jwt_handler.decodificar_token(token.strip())

        try:
            usuario_id = UUID(str(payload.get("sub", "")))
        except (ValueError, TypeError):
            raise InvalidTokenException("El identificador del usuario en el token no es válido.")

        usuario = await self.repo_usuarios.obtener_por_id(usuario_id)
        if not usuario:
            raise InvalidTokenException("El usuario asociado al token no existe.")

        if usuario.estado != "Activo":
            raise AuthFailedException("El usuario se encuentra inactivo o bloqueado.")

        rol_nombre = usuario.rol.nombre if usuario.rol else "ADMINISTRATIVO"

        if usuario.requiere_cambio_password:
            return LoginRequiresPasswordChangeResponse(
                status="requires_password_change",
                message="Debe cambiar su contraseña temporal antes de continuar.",
                data=LoginTempTokenData(
                    temp_token=token,
                    requiere_cambio_password=True,
                ),
            )

        return LoginSuccessResponse(
            status="success",
            data=LoginNormalData(
                token=token,
                user=UserInfoResponse(
                    id=usuario.id,
                    nombre=usuario.nombre,
                    dni=usuario.dni,
                    email=usuario.email,
                    rol=rol_nombre,
                    requiere_cambio_password=False,
                ),
            ),
        )

    async def obtener_usuario_por_id(self, usuario_id: UUID) -> LoginSuccessResponse:
        """Obtiene la información del usuario autenticado actual."""
        usuario = await self.repo_usuarios.obtener_por_id(usuario_id)
        if not usuario:
            raise InvalidTokenException("Usuario no encontrado.")

        if usuario.estado != "Activo":
            raise AuthFailedException("El usuario se encuentra inactivo o bloqueado.")

        rol_nombre = usuario.rol.nombre if usuario.rol else "ADMINISTRATIVO"

        token = self.jwt_handler.emitir_token(
            usuario_id=str(usuario.id),
            rol=rol_nombre,
            scope=ScopeEnum.FULL_ACCESS.value,
        )

        return LoginSuccessResponse(
            status="success",
            data=LoginNormalData(
                token=token,
                user=UserInfoResponse(
                    id=usuario.id,
                    nombre=usuario.nombre,
                    dni=usuario.dni,
                    email=usuario.email,
                    rol=rol_nombre,
                    requiere_cambio_password=usuario.requiere_cambio_password,
                ),
            ),
        )


