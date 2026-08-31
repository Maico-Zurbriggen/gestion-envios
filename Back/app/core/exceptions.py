from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Excepción base para errores de la aplicación con respuesta estructurada."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.errors = errors


class AuthFailedException(AppException):
    def __init__(self, message: str = "Credenciales inválidas."):
        super().__init__(
            message=message,
            code="AUTH_FAILED",
            status_code=401,
        )


class ValidationException(AppException):
    def __init__(
        self,
        message: str = "Los datos proporcionados no son válidos.",
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            errors=errors,
        )


class DuplicateEntryException(AppException):
    def __init__(
        self,
        message: str = "El DNI o Email ya se encuentran registrados.",
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            message=message,
            code="DUPLICATE_ENTRY",
            status_code=409,
            errors=errors,
        )


class PasswordPolicyException(AppException):
    def __init__(
        self,
        message: str = "Las contraseñas no coinciden o no cumplen con los requisitos de seguridad.",
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            message=message,
            code="PASSWORD_POLICY_ERROR",
            status_code=400,
            errors=errors,
        )


class InvalidTokenException(AppException):
    def __init__(self, message: str = "Token de autenticación ausente o inválido."):
        super().__init__(
            message=message,
            code="INVALID_TOKEN",
            status_code=401,
        )


class ForbiddenScopeException(AppException):
    def __init__(
        self,
        message: str = "El token no posee los permisos o alcance necesarios para realizar esta acción.",
    ):
        super().__init__(
            message=message,
            code="FORBIDDEN_SCOPE",
            status_code=403,
        )


class ForbiddenAccessException(AppException):
    def __init__(self, message: str = "Acceso denegado. Se requieren privilegios superiores."):
        super().__init__(
            message=message,
            code="FORBIDDEN_ACCESS",
            status_code=403,
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Recurso no encontrado."):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )

