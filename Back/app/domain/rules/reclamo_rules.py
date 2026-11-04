"""Reglas de dominio de los reclamos iniciados desde la vista pública (HU07).

Funciones puras, sin I/O: qué tipos de reclamo existen y cómo se explican al
público, cuándo un envío admite un reclamo nuevo, cómo se detecta un reclamo
duplicado y qué transiciones de estado puede hacer el personal que lo gestiona.
"""

import re
from collections.abc import Iterable

from app.domain.constants.estados_logistica import EstadoReclamoEnum, TipoReclamoEnum

DESCRIPCIONES_TIPO_RECLAMO: dict[str, str] = {
    TipoReclamoEnum.DEMORA.value: "El envío está demorado o no avanza en el seguimiento.",
    TipoReclamoEnum.DANIO.value: "El paquete llegó dañado o con signos de apertura.",
    TipoReclamoEnum.EXTRAVIO.value: "El paquete se perdió o no aparece.",
    TipoReclamoEnum.OTRO.value: "Cualquier otro inconveniente relacionado con el envío.",
}
"""Texto que acompaña a cada tipo en el formulario público, para que quien
reclama elija el motivo sin conocer los códigos internos."""

ESTADOS_RECLAMO_ACTIVOS: set[str] = {
    EstadoReclamoEnum.ABIERTO.value,
    EstadoReclamoEnum.EN_REVISION.value,
}

ESTADOS_RECLAMO_CERRADOS: set[str] = {
    EstadoReclamoEnum.RESUELTO.value,
    EstadoReclamoEnum.RECHAZADO.value,
}

TRANSICIONES_RECLAMO: dict[str, set[str]] = {
    EstadoReclamoEnum.ABIERTO.value: {
        EstadoReclamoEnum.EN_REVISION.value,
        EstadoReclamoEnum.RESUELTO.value,
        EstadoReclamoEnum.RECHAZADO.value,
    },
    EstadoReclamoEnum.EN_REVISION.value: {
        EstadoReclamoEnum.RESUELTO.value,
        EstadoReclamoEnum.RECHAZADO.value,
    },
    EstadoReclamoEnum.RESUELTO.value: set(),
    EstadoReclamoEnum.RECHAZADO.value: set(),
}
"""Máquina de estados del reclamo. Los estados cerrados no tienen salida: si el
problema reaparece, se inicia un reclamo nuevo, así el historial de lo que se
respondió no se reescribe."""

MAX_RECLAMOS_ACTIVOS_POR_ENVIO = 5
"""Tope de reclamos abiertos o en revisión por envío. El endpoint es público y
sin autenticación (cualquiera con el token puede reclamar), así que el tope
evita que un mismo envío se llene de reclamos repetidos."""

LONGITUD_MINIMA_RESOLUCION = 10
PATRON_TELEFONO = re.compile(r"^\+?[0-9(][0-9\s\-()]{5,29}$")
MIN_DIGITOS_TELEFONO = 6


def normalizar_tipo_reclamo(tipo: str | None) -> str:
    """Pasa el tipo a mayúsculas y sin espacios ("danio " -> "DANIO")."""
    return (tipo or "").strip().upper()


def es_tipo_reclamo_valido(tipo: str | None) -> bool:
    return normalizar_tipo_reclamo(tipo) in DESCRIPCIONES_TIPO_RECLAMO


def es_estado_reclamo_valido(estado: str | None) -> bool:
    return (estado or "").strip().upper() in TRANSICIONES_RECLAMO


def evaluar_habilitacion_reclamo(cantidad_reclamos_activos: int) -> tuple[bool, str | None]:
    """Indica si el envío admite iniciar un reclamo nuevo (HU07 Escenario 1).

    Retorna `(habilitado, motivo_no_habilitado)`.
    """
    if cantidad_reclamos_activos >= MAX_RECLAMOS_ACTIVOS_POR_ENVIO:
        return False, (
            f"El envío ya tiene {cantidad_reclamos_activos} reclamos abiertos o en revisión. "
            "Esperá la respuesta de los reclamos en curso antes de iniciar uno nuevo."
        )
    return True, None


def es_reclamo_duplicado(
    tipo: str,
    paquete_id: object | None,
    reclamos_activos: Iterable[tuple[str, object | None]],
) -> bool:
    """Detecta si ya hay un reclamo activo del mismo tipo sobre el mismo objetivo.

    El objetivo es el paquete puntual o, si `paquete_id` es `None`, el envío
    completo. `reclamos_activos` son pares `(tipo, paquete_id)` de los reclamos
    abiertos o en revisión del envío.
    """
    tipo_normalizado = normalizar_tipo_reclamo(tipo)
    return any(
        normalizar_tipo_reclamo(tipo_existente) == tipo_normalizado and paquete_existente == paquete_id
        for tipo_existente, paquete_existente in reclamos_activos
    )


def validar_contacto_reclamo(email: str | None, telefono: str | None) -> list[dict[str, str]]:
    """Exige al menos un medio de contacto válido.

    El reclamo se inicia sin sesión, así que el email o el teléfono que se
    cargan acá son la única forma de responderle a quien reclama.
    """
    errores: list[dict[str, str]] = []
    email_limpio = (email or "").strip()
    telefono_limpio = (telefono or "").strip()

    if not email_limpio and not telefono_limpio:
        errores.append({
            "field": "contacto",
            "message": "Debe indicar al menos un medio de contacto: email o teléfono.",
        })
        return errores

    if telefono_limpio:
        if not PATRON_TELEFONO.match(telefono_limpio):
            errores.append({
                "field": "contacto_telefono",
                "message": "El teléfono solo puede contener dígitos, espacios, guiones, paréntesis y un '+' inicial.",
            })
        elif sum(c.isdigit() for c in telefono_limpio) < MIN_DIGITOS_TELEFONO:
            errores.append({
                "field": "contacto_telefono",
                "message": f"El teléfono debe tener al menos {MIN_DIGITOS_TELEFONO} dígitos.",
            })

    return errores


def validar_transicion_reclamo(
    estado_actual: str,
    estado_nuevo: str,
    resolucion: str | None,
) -> list[dict[str, str]]:
    """Valida el cambio de estado que pide quien gestiona el reclamo.

    Cerrar un reclamo (`RESUELTO` o `RECHAZADO`) exige una resolución escrita:
    es lo que ve quien reclamó en la vista pública.
    """
    errores: list[dict[str, str]] = []
    actual = (estado_actual or "").strip().upper()
    nuevo = (estado_nuevo or "").strip().upper()

    if nuevo not in TRANSICIONES_RECLAMO:
        errores.append({
            "field": "estado",
            "message": f"Estado de reclamo inválido. Valores aceptados: {', '.join(TRANSICIONES_RECLAMO)}.",
        })
        return errores

    if nuevo == actual:
        errores.append({"field": "estado", "message": f"El reclamo ya se encuentra en estado '{actual}'."})
        return errores

    permitidos = TRANSICIONES_RECLAMO.get(actual, set())
    if nuevo not in permitidos:
        if actual in ESTADOS_RECLAMO_CERRADOS:
            mensaje = f"El reclamo ya está cerrado ({actual}) y no admite cambios de estado."
        else:
            mensaje = f"No se puede pasar un reclamo de '{actual}' a '{nuevo}'."
        errores.append({"field": "estado", "message": mensaje})
        return errores

    if nuevo in ESTADOS_RECLAMO_CERRADOS and len((resolucion or "").strip()) < LONGITUD_MINIMA_RESOLUCION:
        errores.append({
            "field": "resolucion",
            "message": (
                f"Para cerrar el reclamo debe indicar una resolución de al menos "
                f"{LONGITUD_MINIMA_RESOLUCION} caracteres."
            ),
        })

    return errores
