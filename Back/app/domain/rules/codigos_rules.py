import re
import secrets
import string

ALFABETO_CODIGOS = string.ascii_uppercase + string.digits
LONGITUD_SUFIJO = 10
PREFIJO_TOKEN_SEGUIMIENTO = "ENV-"
PREFIJO_NUMERO_PAQUETE = "PAQ-"


def _generar_sufijo() -> str:
    return "".join(secrets.choice(ALFABETO_CODIGOS) for _ in range(LONGITUD_SUFIJO))


def generar_token_seguimiento() -> str:
    """Genera un token público de seguimiento criptográficamente aleatorio (HU03/HU04)."""
    return f"{PREFIJO_TOKEN_SEGUIMIENTO}{_generar_sufijo()}"


def generar_numero_paquete() -> str:
    """Genera un número de paquete público (codificado en el código de barras de la planilla)."""
    return f"{PREFIJO_NUMERO_PAQUETE}{_generar_sufijo()}"


def normalizar_token_seguimiento(token: str | None) -> str:
    """Limpia el token que tipea o pega el usuario en la vista pública.

    Los tokens se generan siempre en mayúsculas y sin espacios, pero quien lo
    copia de un correo suele arrastrar espacios o saltos de línea, y quien lo
    tipea puede hacerlo en minúsculas. Sin esta normalización, `env-adrzspq90k`
    devolvía `404` aunque el envío exista.
    """
    return re.sub(r"\s+", "", token or "").upper()
