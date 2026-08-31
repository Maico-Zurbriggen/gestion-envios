from datetime import timedelta
import pytest

from app.core.exceptions import InvalidTokenException
from app.domain.constants.roles import RolEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT


def test_emitir_y_decodificar_token_full_access():
    """Verifica emisión y decodificación de token con scope FULL_ACCESS."""
    usuario_id = "11111111-2222-3333-4444-555555555555"
    rol = RolEnum.SUPERADMIN.value

    token = ManejadorJWT.emitir_token(
        usuario_id=usuario_id,
        rol=rol,
        scope=ScopeEnum.FULL_ACCESS.value,
    )

    payload = ManejadorJWT.decodificar_token(token)
    assert payload["sub"] == usuario_id
    assert payload["rol"] == rol
    assert payload["scope"] == ScopeEnum.FULL_ACCESS.value
    assert "exp" in payload
    assert "iat" in payload


def test_emitir_y_decodificar_token_temp():
    """Verifica emisión de token temporal con scope PASSWORD_RESET_ONLY."""
    usuario_id = "22222222-3333-4444-5555-666666666666"
    rol = RolEnum.ADMINISTRATIVO.value

    token = ManejadorJWT.emitir_token(
        usuario_id=usuario_id,
        rol=rol,
        scope=ScopeEnum.PASSWORD_RESET_ONLY.value,
    )

    payload = ManejadorJWT.decodificar_token(token)
    assert payload["sub"] == usuario_id
    assert payload["rol"] == rol
    assert payload["scope"] == ScopeEnum.PASSWORD_RESET_ONLY.value


def test_token_expirado_lanza_excepcion():
    """Verifica que un token expirado lance InvalidTokenException."""
    usuario_id = "33333333-4444-5555-6666-777777777777"
    token = ManejadorJWT.emitir_token(
        usuario_id=usuario_id,
        rol=RolEnum.VENDEDOR.value,
        expiracion_delta=timedelta(seconds=-10),  # Expirado en el pasado
    )

    with pytest.raises(InvalidTokenException) as exc_info:
        ManejadorJWT.decodificar_token(token)
    assert "ha expirado" in exc_info.value.message


def test_token_invalido_o_adulterado_lanza_excepcion():
    """Verifica que un token manipulado sea rechazado."""
    with pytest.raises(InvalidTokenException):
        ManejadorJWT.decodificar_token("token.falso.invalido")

