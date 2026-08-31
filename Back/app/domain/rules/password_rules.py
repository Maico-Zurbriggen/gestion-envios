import re
import secrets
import string
from typing import Optional, Tuple

CARACTERES_ESPECIALES_PERMITIDOS = "!@#$%&*"
LETRAS_MINUSCULAS = string.ascii_lowercase
LETRAS_MAYUSCULAS = string.ascii_uppercase
DIGITOS = string.digits


def generar_password_temporal(longitud: int = 12) -> str:
    """Genera una contraseña temporal criptográficamente segura.
    
    Cumple con la política de la Adenda Sección B:
    - Longitud entre 10 y 12 caracteres.
    - Al menos una mayúscula, una minúscula, un número y un símbolo especial (!@#$%&*).
    - Utiliza secrets (PRNG criptográfico).
    """
    if longitud < 10 or longitud > 12:
        longitud = 12

    # Asegurar al menos un carácter de cada tipo requerido
    password_chars = [
        secrets.choice(LETRAS_MAYUSCULAS),
        secrets.choice(LETRAS_MINUSCULAS),
        secrets.choice(DIGITOS),
        secrets.choice(CARACTERES_ESPECIALES_PERMITIDOS),
    ]

    # Completar el resto con el pool completo
    pool_completo = LETRAS_MAYUSCULAS + LETRAS_MINUSCULAS + DIGITOS + CARACTERES_ESPECIALES_PERMITIDOS
    caracteres_restantes = longitud - len(password_chars)
    for _ in range(caracteres_restantes):
        password_chars.append(secrets.choice(pool_completo))

    # Mezclar criptográficamente
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def validar_politica_password(password: str) -> Tuple[bool, Optional[str]]:
    """Valida que una contraseña cumpla con la política unificada del sistema.
    
    Reglas:
    - Longitud mínima de 10 caracteres.
    - Al menos una letra mayúscula.
    - Al menos una letra minúscula.
    - Al menos un dígito numérico.
    - Al menos un símbolo especial (!@#$%&*).
    """
    if not password or len(password) < 10:
        return False, "La contraseña debe tener al menos 10 caracteres."

    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una letra mayúscula."

    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una letra minúscula."

    if not re.search(r"[0-9]", password):
        return False, "La contraseña debe contener al menos un número."

    # Permite los símbolos de la adenda: ! @ # $ % & * (y caracteres de puntuación estándar)
    if not re.search(r"[!@#$%&*]", password):
        return False, "La contraseña debe contener al menos un carácter especial (! @ # $ % & *)."

    return True, None

