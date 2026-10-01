"""Reglas de dominio para el retiro de paquetes en sucursal (HU13).

Contiene validaciones puras de negocio sobre condiciones de retiro, mayoría
de edad del titular (>= 16 años), requisitos de presentación para terceros
autorizados y estados válidos del paquete.
"""

from typing import Any, Dict, List, Optional

from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoRetiroEnum

ESTADOS_VALIDOS_PARA_RETIRO: set[str] = {
    EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
    EstadoPaqueteEnum.EN_SUCURSAL.value,
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
    # "Pendiente" o "PENDIENTE" si fue registrado para entrega en sucursal y ya está disponible
    "Pendiente",
    EstadoPaqueteEnum.PENDIENTE.value,
}

ESTADOS_YA_ENTREGADOS: set[str] = {
    EstadoPaqueteEnum.ENTREGADO.value,
    EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
    EstadoPaqueteEnum.RETIRADO.value,
}


def evaluar_disponibilidad_retiro(estado_actual: str) -> tuple[bool, Optional[str]]:
    """Evalúa si un estado de paquete permite realizar el retiro en sucursal.
    
    Retorna una tupla (disponible: bool, motivo: Optional[str]).
    """
    estado_normalizado = estado_actual.strip()

    if estado_normalizado in ESTADOS_YA_ENTREGADOS:
        return False, "El paquete ya fue entregado o retirado previamente."

    if estado_normalizado in ESTADOS_VALIDOS_PARA_RETIRO:
        return True, None

    return False, (
        f"El paquete no se encuentra listo para retiro en sucursal. "
        f"Estado actual: '{estado_actual}'. Debe estar en sucursal para poder retirarse."
    )


def validar_requisitos_retiro(
    tipo_retiro: str,
    destinatario_mayor_16: bool,
    documento_tipo: str,
    documento_numero: str,
    tercero_datos: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Valida los requisitos de identidad y documentación para el retiro de un paquete.
    
    Retorna una lista de errores estructurados [{"field": ..., "message": ...}].
    Si la lista está vacía, todos los requisitos de negocio se cumplen.
    """
    errores: List[Dict[str, str]] = []

    # 1. Regla: Destinatario titular debe tener al menos 16 años
    if not destinatario_mayor_16:
        errores.append({
            "field": "destinatario_mayor_16",
            "message": "El titular o destinatario debe tener al menos 16 años para retirar o autorizar el retiro.",
        })

    # 2. Documento presentado
    if not documento_tipo or not documento_tipo.strip():
        errores.append({
            "field": "documento_presentado.tipo",
            "message": "Debe especificar el tipo de documento presentado.",
        })
    if not documento_numero or not documento_numero.strip():
        errores.append({
            "field": "documento_presentado.numero",
            "message": "Debe especificar el número de documento presentado.",
        })

    # 3. Validaciones según tipo de retiro
    tipo_normalizado = tipo_retiro.strip().upper() if tipo_retiro else ""
    if tipo_normalizado not in {TipoRetiroEnum.TITULAR.value, TipoRetiroEnum.TERCERO_AUTORIZADO.value}:
        errores.append({
            "field": "tipo_retiro",
            "message": f"Tipo de retiro inválido. Valores aceptados: '{TipoRetiroEnum.TITULAR.value}', '{TipoRetiroEnum.TERCERO_AUTORIZADO.value}'.",
        })
        return errores

    if tipo_normalizado == TipoRetiroEnum.TERCERO_AUTORIZADO.value:
        if not tercero_datos:
            errores.append({
                "field": "tercero_autorizado",
                "message": "Debe proporcionar los datos del tercero autorizado cuando el tipo de retiro es TERCERO_AUTORIZADO.",
            })
            return errores

        nombre_tercero = tercero_datos.get("nombre_completo", "")
        if not nombre_tercero or not str(nombre_tercero).strip():
            errores.append({
                "field": "tercero_autorizado.nombre_completo",
                "message": "Debe indicar el nombre completo del tercero autorizado.",
            })

        doc_tercero = tercero_datos.get("documento", "")
        if not doc_tercero or not str(doc_tercero).strip():
            errores.append({
                "field": "tercero_autorizado.documento",
                "message": "Debe indicar el número de documento del tercero autorizado.",
            })

        posee_copia = bool(tercero_datos.get("posee_copia_dni_titular", False))
        if not posee_copia:
            errores.append({
                "field": "tercero_autorizado.posee_copia_dni_titular",
                "message": "Es requisito excluyente presentar una copia física o digital del documento de identidad del destinatario titular.",
            })

        posee_nota = bool(tercero_datos.get("posee_nota_autorizacion", False))
        if not posee_nota:
            errores.append({
                "field": "tercero_autorizado.posee_nota_autorizacion",
                "message": "Es requisito excluyente presentar el formulario o nota de autorización de retiro firmada por el titular.",
            })

    return errores
