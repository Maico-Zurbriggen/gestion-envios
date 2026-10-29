"""Reglas de dominio para el retiro de paquetes en sucursal (HU09 y HU13).

Contiene validaciones puras de negocio sobre condiciones de retiro, edad de
quien retira (mayor de 16 años), requisitos de presentación para terceros
autorizados, modalidad y sucursal del envío y estados válidos del paquete.

HU13 las usa para habilitar el registro del retiro en ventanilla; HU09 reusa
las mismas reglas de estado para informar, en la vista pública, si el paquete
ya está disponible para que el destinatario lo pase a buscar.
"""

from typing import Any

from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoRetiroEnum

ESTADOS_VALIDOS_PARA_RETIRO: set[str] = {
    EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
    EstadoPaqueteEnum.EN_SUCURSAL.value,
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
}
"""Solo un paquete que llegó físicamente a la sucursal se puede retirar. Un
paquete pendiente todavía no ingresó a la red (HU06): entregarlo sería
registrar un retiro de algo que la sucursal no tiene."""

ESTADOS_YA_ENTREGADOS: set[str] = {
    EstadoPaqueteEnum.ENTREGADO.value,
    EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
    EstadoPaqueteEnum.RETIRADO.value,
    EstadoPaqueteEnum.DEVUELTO.value,
}


def evaluar_disponibilidad_retiro(estado_actual: str) -> tuple[bool, str | None]:
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
    tercero_datos: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Valida los requisitos de identidad y documentación para el retiro de un paquete.

    Retorna una lista de errores estructurados [{"field": ..., "message": ...}].
    Si la lista está vacía, todos los requisitos de negocio se cumplen.
    """
    errores: list[dict[str, str]] = []

    # 1. Regla: el destinatario titular debe ser mayor de 16 años
    if not destinatario_mayor_16:
        errores.append({
            "field": "destinatario_mayor_16",
            "message": "El destinatario titular debe ser mayor de 16 años para retirar o autorizar el retiro.",
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


# --- HU09: opciones de retiro en sucursal desde la experiencia pública ---

TIPO_ENTREGA_SUCURSAL = "sucursal"
TIPO_ENTREGA_DOMICILIO = "domicilio"
"""Valores que `EnvioModel.tipo_entrega` toma desde el registro de HU03."""


def envio_habilita_retiro_en_sucursal(tipo_entrega: str) -> tuple[bool, str | None]:
    """Evalúa si un envío se gestiona para retiro en sucursal (HU09 Escenario 1).

    Es la condición "DADO que el envío se gestiona para retiro y no para
    entrega a domicilio" del criterio de aceptación. Retorna
    `(aplica, motivo_no_aplica)`.
    """
    tipo_normalizado = (tipo_entrega or "").strip().lower()

    if tipo_normalizado == TIPO_ENTREGA_SUCURSAL:
        return True, None

    if tipo_normalizado == TIPO_ENTREGA_DOMICILIO:
        return False, (
            "Este envío se entrega en el domicilio del destinatario, "
            "por lo que no requiere retiro en sucursal."
        )

    return False, (
        f"No se puede determinar la modalidad de entrega del envío (tipo_entrega: '{tipo_entrega}')."
    )


ESTADOS_YA_EN_SUCURSAL_DESTINO: set[str] = set(ESTADOS_VALIDOS_PARA_RETIRO)
"""Estados en los que el paquete está físicamente en la sucursal de destino:
los mismos que habilitan el mostrador de HU13, para que la vista pública de
HU09 nunca anuncie como disponible algo que el personal no puede entregar."""


def paquete_disponible_en_sucursal(estado_actual: str) -> bool:
    """Indica si el paquete ya llegó a la sucursal y se puede pasar a buscar.

    Alimenta el campo `disponible_para_retirar` de la vista pública de HU09.
    """
    return (estado_actual or "").strip() in ESTADOS_YA_EN_SUCURSAL_DESTINO


def validar_envio_para_retiro(
    tipo_entrega: str,
    sucursal_retiro_id: int | None,
    sucursal_actual_id: int | None,
    sucursal_operador_id: int | None,
) -> list[dict[str, str]]:
    """HU13: el paquete tiene que estar en su sucursal de retiro, que además tiene que
    ser la sucursal donde atiende el personal que registra el retiro.

    La sucursal de retiro la resuelve `circuito_rules.sucursal_de_retiro`: la elegida
    por el cliente, la que quedó tras las visitas a domicilio o, en una devolución,
    la de origen.
    """
    errores: list[dict[str, str]] = []
    if sucursal_retiro_id is None:
        aplica, motivo = envio_habilita_retiro_en_sucursal(tipo_entrega)
        errores.append({
            "field": "tipo_entrega",
            "message": (motivo if not aplica else None) or "El paquete no se retira en sucursal.",
        })
        return errores
    if sucursal_actual_id != sucursal_retiro_id:
        errores.append({
            "field": "sucursal_actual",
            "message": "El paquete todavía no está en la sucursal donde se retira.",
        })
    if sucursal_operador_id is not None and sucursal_operador_id != sucursal_retiro_id:
        errores.append({
            "field": "sucursal_id",
            "message": "El paquete se retira en otra sucursal: no puede entregarse en esta.",
        })
    return errores


def validar_receptor_retiro(
    tipo_retiro: str,
    receptor_mayor_16: bool,
    documento_original_verificado: bool,
    documento_presentado: str,
    documento_tercero: str | None,
) -> list[dict[str, str]]:
    """HU13: quien retira debe ser mayor de 16 años y haber exhibido su documento original.

    Si retira un tercero, el documento presentado es el propio y debe coincidir
    con el declarado en la autorización.
    """
    errores: list[dict[str, str]] = []
    if not receptor_mayor_16:
        errores.append({
            "field": "receptor_fecha_nacimiento",
            "message": "La persona que retira debe ser mayor de 16 años.",
        })
    if not documento_original_verificado:
        errores.append({
            "field": "documento_original_verificado",
            "message": "Debe verificar el documento original de quien retira.",
        })
    if (
        (tipo_retiro or "").strip().upper() == TipoRetiroEnum.TERCERO_AUTORIZADO.value
        and documento_tercero
        and documento_tercero.strip() != (documento_presentado or "").strip()
    ):
        errores.append({
            "field": "tercero_autorizado.documento",
            "message": "El documento del tercero autorizado debe coincidir con el documento presentado.",
        })
    return errores
