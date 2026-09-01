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
