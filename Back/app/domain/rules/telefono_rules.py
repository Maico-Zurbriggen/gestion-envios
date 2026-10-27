"""Normalización de teléfonos para WhatsApp (HU05 y aviso de visita de HU12).

Los teléfonos se registran como texto libre en HU03 (`+543564112233`,
`3564 15 400010`, `011-1234-5678`...). WhatsApp identifica cada cuenta por su
número internacional E.164 sin símbolos. En Argentina los celulares llevan un
`9` después del código de país (`549` + área + número) y nunca el `0` de
discado nacional ni el `15` local.
"""

import re

CODIGO_PAIS_ARGENTINA = "54"
LONGITUD_NACIONAL_ARGENTINA = 10
"""Código de área + número de abonado, sin 0 ni 15 (ej. 3564400010)."""

MIN_DIGITOS_E164 = 8
MAX_DIGITOS_E164 = 15


def _quitar_15_local(digitos: str) -> str:
    """Quita el `15` de celular que se marca después del código de área (2 a 4 dígitos)."""
    if len(digitos) != LONGITUD_NACIONAL_ARGENTINA + 2:
        return digitos
    for posicion in (2, 3, 4):
        if digitos[posicion : posicion + 2] == "15":
            return digitos[:posicion] + digitos[posicion + 2 :]
    return digitos


def _normalizar_argentina(nacional: str) -> str | None:
    nacional = nacional.lstrip("0")
    if nacional.startswith("9") and len(nacional) == LONGITUD_NACIONAL_ARGENTINA + 1:
        nacional = nacional[1:]
    nacional = _quitar_15_local(nacional)
    if len(nacional) != LONGITUD_NACIONAL_ARGENTINA:
        return None
    return f"{CODIGO_PAIS_ARGENTINA}9{nacional}"


def normalizar_telefono_whatsapp(telefono: str | None, codigo_pais: str = CODIGO_PAIS_ARGENTINA) -> str | None:
    """Devuelve el número E.164 sin `+` que espera WhatsApp, o `None` si no es utilizable.

    - Con `+` o `00` se respeta el código de país indicado.
    - Sin código de país se asume `codigo_pais` (Argentina por defecto).
    - Para Argentina se agrega el `9` de celular y se quitan `0` y `15`.
    """
    if not telefono:
        return None
    texto = telefono.strip()
    internacional = texto.startswith("+") or texto.startswith("00")
    digitos = re.sub(r"\D", "", texto)
    if internacional and digitos.startswith("00"):
        digitos = digitos[2:]

    resultado: str | None
    if internacional or (digitos.startswith(codigo_pais) and len(digitos) > LONGITUD_NACIONAL_ARGENTINA):
        if digitos.startswith(CODIGO_PAIS_ARGENTINA):
            resultado = _normalizar_argentina(digitos[len(CODIGO_PAIS_ARGENTINA) :])
        else:
            resultado = digitos
    elif codigo_pais == CODIGO_PAIS_ARGENTINA:
        resultado = _normalizar_argentina(digitos)
    else:
        resultado = f"{codigo_pais}{digitos.lstrip('0')}"

    if resultado is None or not MIN_DIGITOS_E164 <= len(resultado) <= MAX_DIGITOS_E164:
        return None
    return resultado


def enmascarar_telefono(telefono: str) -> str:
    """Oculta los dígitos centrales para registros y respuestas operativas."""
    digitos = re.sub(r"\D", "", telefono or "")
    if len(digitos) <= 4:
        return "****"
    return f"+{digitos[:2]}******{digitos[-4:]}"
