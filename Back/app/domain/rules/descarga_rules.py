"""Control de descarga en la sucursal de destino: reglas puras.

Cuando un recorrido de larga distancia llega a una sucursal, el personal
escanea cada paquete que baja. Cada lectura se compara con los paquetes que
ese recorrido tenía que dejar en esa sucursal.
"""

import re

from app.domain.constants.estados_logistica import EstadoRecorridoEnum

CORRECTO = "CORRECTO"
SOBRANTE = "SOBRANTE"
DESCONOCIDO = "DESCONOCIDO"

EN_CURSO = "EN_CURSO"
CERRADO = "CERRADO"

ESTADOS_RECORRIDO_CONTROLABLES = (EstadoRecorridoEnum.EN_CURSO.value, EstadoRecorridoEnum.FINALIZADO.value)
"""Solo se descarga lo que ya salió: un recorrido generado todavía no viajó."""

DIAS_RECORRIDOS_ENTRANTES = 7
"""Recorridos de los últimos días que se ofrecen para controlar."""

_PATRON_PAQUETE = re.compile(r"^PAQ-[A-Z0-9]{10}$")


def normalizar_codigo(codigo: str) -> str:
    """Mayúsculas y sin espacios: los lectores USB y la cámara a veces agregan espacios o minúsculas."""
    return re.sub(r"\s+", "", codigo or "").upper()


def es_codigo_de_paquete(codigo: str) -> bool:
    return bool(_PATRON_PAQUETE.match(codigo))


def motivo_sobrante(
    *,
    es_del_recorrido: bool,
    sucursal_destino_del_paquete: str | None,
    sucursal_control: str,
) -> str:
    """Explica por qué un paquete leído no correspondía a esta descarga."""
    if es_del_recorrido and sucursal_destino_del_paquete:
        return f"Viaja en este recorrido pero baja en {sucursal_destino_del_paquete}. Volvelo a cargar."
    if es_del_recorrido:
        return "Viaja en este recorrido pero no corresponde a esta sucursal."
    return f"No figura en este recorrido para {sucursal_control}. Separalo y revisá su trazabilidad."


def resumen_control(esperados: int, verificados: int, sobrantes: int) -> str:
    faltantes = max(esperados - verificados, 0)
    partes = [f"{verificados} de {esperados} paquetes verificados"]
    if faltantes:
        partes.append(f"{faltantes} {'faltante' if faltantes == 1 else 'faltantes'}")
    if sobrantes:
        partes.append(f"{sobrantes} {'sobrante' if sobrantes == 1 else 'sobrantes'}")
    return ", ".join(partes) + "."
