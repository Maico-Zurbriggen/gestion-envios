from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app.core.config import settings
from app.core.exceptions import InvalidTokenException
from app.domain.constants.scopes import ScopeEnum


class ManejadorJWT:
    """Manejador para la emisión y verificación de JSON Web Tokens (JWT)."""

    @staticmethod
    def emitir_token(
        usuario_id: str,
        rol: str,
        scope: str = ScopeEnum.FULL_ACCESS.value,
        expiracion_delta: timedelta | None = None,
    ) -> str:
        """Emite un token JWT firmado."""
        ahora = datetime.now(UTC)
        if expiracion_delta is None:
            if scope == ScopeEnum.PASSWORD_RESET_ONLY.value:
                expiracion_delta = settings.jwt_temp_token_expiration_timedelta
            else:
                expiracion_delta = settings.jwt_expiration_timedelta

        expiracion = ahora + expiracion_delta

        payload: dict[str, Any] = {
            "sub": str(usuario_id),
            "rol": rol,
            "scope": scope,
            "iat": ahora,
            "exp": expiracion,
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        return token

    @staticmethod
    def decodificar_token(token: str) -> dict[str, Any]:
        """Decodifica y valida un token JWT."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except ExpiredSignatureError:
            raise InvalidTokenException("El token ha expirado.")
        except PyJWTError:
            raise InvalidTokenException("Token de autenticación inválido.")

