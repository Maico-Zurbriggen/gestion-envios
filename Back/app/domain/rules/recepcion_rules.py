"""Reglas de dominio para la recepción de paquetes en la terminal (HU06).

Contiene validaciones puras, sin I/O, sobre el código de barras que el
vendedor escanea de la planilla impresa y sobre los estados de paquete que
habilitan registrarlo como recibido en la terminal.
"""

import re
import uuid
from typing import Dict, List, Optional

from app.domain.constants.estados_logistica import EstadoPaqueteEnum
from app.domain.rules.codigos_rules import LONGITUD_SUFIJO, PREFIJO_NUMERO_PAQUETE

PATRON_NUMERO_PAQUETE = re.compile(
    rf"^{PREFIJO_NUMERO_PAQUETE}[A-Z0-9]{{{LONGITUD_SUFIJO}}}$"
)
"""Formato que genera `codigos_rules.generar_numero_paquete` y que la planilla
de HU03 codifica en el código de barras CODE128 (ej. `PAQ-ZPC5LB48JJ`)."""

ESTADOS_VALIDOS_PARA_RECEPCION: set[str] = {
    # HU03 crea los paquetes con el literal "Pendiente"; el enum se usa desde
    # HU06 en adelante. Se aceptan las dos escrituras para no romper los
    # envíos precargados antes de esta historia.
    "Pendiente",
    EstadoPaqueteEnum.PENDIENTE.value,
}

ESTADOS_YA_RECEPCIONADOS: set[str] = {
    EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value,
    EstadoPaqueteEnum.EN_TRANSITO.value,
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
    EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
    EstadoPaqueteEnum.EN_SUCURSAL.value,
    EstadoPaqueteEnum.EN_REPARTO.value,
}

ESTADOS_CICLO_CERRADO: set[str] = {
    EstadoPaqueteEnum.ENTREGADO.value,
    EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
    EstadoPaqueteEnum.RETIRADO.value,
}


def normalizar_codigo_escaneado(codigo: str) -> str:
    """Limpia el valor que llega del lector de código de barras.

    Los lectores suelen agregar espacios, saltos de línea o un Enter final, y
    algunos emiten el texto en minúsculas. Se eliminan todos los espacios en
    blanco internos y se pasa a mayúsculas para que el valor quede idéntico al
    `numero_paquete` persistido.
    """
    if not codigo:
        return ""
    return re.sub(r"\s+", "", codigo).upper()


def es_numero_paquete(codigo: str) -> bool:
    """Indica si el código normalizado tiene el formato `PAQ-XXXXXXXXXX`."""
    return bool(PATRON_NUMERO_PAQUETE.match(codigo))


def es_uuid_paquete(codigo: str) -> bool:
    """Indica si el código normalizado es un UUID (el `id` interno del paquete).

    Se admite además del número de paquete porque el frontend puede reusar el
    mismo endpoint pasando el identificador que ya tiene en memoria, sin
    necesidad de volver a escanear.
    """
    try:
        uuid.UUID(codigo)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def validar_codigo_escaneado(codigo: str) -> List[Dict[str, str]]:
    """Valida el formato del código escaneado antes de ir a la base de datos.

    Retorna una lista de errores estructurados `[{"field", "message"}]`; vacía
    si el código es utilizable.
    """
    errores: List[Dict[str, str]] = []
    normalizado = normalizar_codigo_escaneado(codigo)

    if not normalizado:
        errores.append({
            "field": "codigo",
            "message": "Debe indicar el código de barras de la planilla del paquete.",
        })
        return errores

    if not es_numero_paquete(normalizado) and not es_uuid_paquete(normalizado):
        errores.append({
            "field": "codigo",
            "message": (
                f"El código escaneado no tiene un formato válido. Se espera el número de paquete "
                f"'{PREFIJO_NUMERO_PAQUETE}XXXXXXXXXX' impreso en la planilla o el identificador interno del paquete."
            ),
        })

    return errores


def evaluar_disponibilidad_recepcion(estado_actual: str) -> tuple[bool, Optional[str]]:
    """Evalúa si el estado actual del paquete permite recibirlo en la terminal.

    Retorna `(disponible, motivo)`: `motivo` es `None` cuando se puede recibir y
    un texto explicativo para mostrar en pantalla cuando no.
    """
    estado_normalizado = (estado_actual or "").strip()

    if estado_normalizado in ESTADOS_CICLO_CERRADO:
        return False, "El paquete ya completó su ciclo de entrega y no puede volver a recibirse en la terminal."

    if estado_normalizado in ESTADOS_YA_RECEPCIONADOS:
        return False, (
            f"El paquete ya fue recibido y está circulando en la red. Estado actual: '{estado_normalizado}'."
        )

    if estado_normalizado in ESTADOS_VALIDOS_PARA_RECEPCION:
        return True, None

    return False, (
        f"El paquete no se encuentra en un estado que permita la recepción en terminal. "
        f"Estado actual: '{estado_normalizado}'. Debe estar pendiente de ingreso."
    )
