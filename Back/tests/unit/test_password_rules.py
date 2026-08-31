import re
from app.domain.rules.password_rules import (
    generar_password_temporal,
    validar_politica_password,
)


def test_generar_password_temporal_cumple_politica():
    """Verifica que la generación de contraseñas temporales cumpla siempre con la Adenda Sección B."""
    for _ in range(100):
        pwd = generar_password_temporal()
        assert 10 <= len(pwd) <= 12, f"Longitud incorrecta: {len(pwd)}"
        assert re.search(r"[A-Z]", pwd), "Falta mayúscula en contraseña generada"
        assert re.search(r"[a-z]", pwd), "Falta minúscula en contraseña generada"
        assert re.search(r"[0-9]", pwd), "Falta dígito en contraseña generada"
        assert re.search(r"[!@#$%&*]", pwd), "Falta carácter especial en contraseña generada"
        
        # Validar con la función de política
        es_valida, error = validar_politica_password(pwd)
        assert es_valida is True, f"La contraseña generada fue rechazada por la política: {error}"


def test_validar_politica_password_casos_validos():
    """Verifica contraseñas válidas que cumplen todos los requisitos."""
    passwords_validas = [
        "ClaveSegura123!",
        "Tmp#9284Kz1",
        "P@ssword2026",
        "MiNuevaPasswordSegura2026!",
        "SuperAdmin2026!*",
        "abcDEF1234$",
    ]
    for pwd in passwords_validas:
        es_valida, error = validar_politica_password(pwd)
        assert es_valida is True, f"Esperado válido para '{pwd}', pero falló: {error}"
        assert error is None


def test_validar_politica_password_casos_invalidos():
    """Verifica el rechazo de contraseñas que violan las reglas de la política."""
    # Menor a 10 caracteres
    valida, error = validar_politica_password("Ab1!cde")
    assert valida is False
    assert "al menos 10 caracteres" in error

    # Sin mayúscula
    valida, error = validar_politica_password("passwordsegura123!")
    assert valida is False
    assert "mayúscula" in error

    # Sin minúscula
    valida, error = validar_politica_password("PASSWORDSEGURA123!")
    assert valida is False
    assert "minúscula" in error

    # Sin número
    valida, error = validar_politica_password("PasswordSegura!")
    assert valida is False
    assert "número" in error

    # Sin carácter especial
    valida, error = validar_politica_password("PasswordSegura123")
    assert valida is False
    assert "carácter especial" in error

