"""Reglas puras del circuito logístico, del registro a la entrega o la devolución.

Siguen la práctica de los correos del país (Correo Argentino, Andreani, OCA):
el envío se registra online y se admite en una sucursal, viaja escaneado en
cada traspaso, se visita hasta dos veces y, si no se entrega, espera en una
sucursal un plazo de días hábiles antes de volver al remitente.
"""

from datetime import UTC, datetime, timedelta

from app.domain.constants.estados_logistica import EstadoPaqueteEnum as E

ESTADOS_PRE_REGISTRO = ("Pendiente", E.PENDIENTE.value)
"""Registrado por el cliente, todavía sin admitir en una sucursal."""

ESTADOS_ESPERANDO_RETIRO = (E.LISTO_PARA_RETIRO.value, E.EN_SUCURSAL_DESTINO.value, E.EN_SUCURSAL.value)


def sumar_dias_habiles(desde: datetime, dias: int) -> datetime:
    """`desde` + `dias` hábiles (lunes a viernes), al final de ese día en hora argentina."""
    local = desde.astimezone(UTC) - timedelta(hours=3)
    fecha = local.date()
    restantes = dias
    while restantes > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            restantes -= 1
    fin_del_dia_local = datetime(fecha.year, fecha.month, fecha.day, 23, 59, 59, tzinfo=UTC)
    return fin_del_dia_local + timedelta(hours=3)


def pre_registro_vencido(estado: str, creado: datetime, ahora: datetime, dias: int) -> bool:
    """Un envío registrado online que no se llevó a una sucursal dentro del plazo."""
    if estado not in ESTADOS_PRE_REGISTRO:
        return False
    creado_utc = creado if creado.tzinfo else creado.replace(tzinfo=UTC)
    return ahora - creado_utc > timedelta(days=dias)


def retiro_vencido(estado: str, retiro_hasta: datetime | None, en_devolucion: bool, ahora: datetime) -> bool:
    """El destinatario no lo retiró a tiempo. Lo que ya vuelve al remitente no vence de nuevo."""
    if en_devolucion or retiro_hasta is None or estado not in ESTADOS_ESPERANDO_RETIRO:
        return False
    limite = retiro_hasta if retiro_hasta.tzinfo else retiro_hasta.replace(tzinfo=UTC)
    return ahora > limite


def sucursal_de_retiro(
    *,
    tipo_entrega: str | None,
    sucursal_destino_id: int | None,
    sucursal_actual_id: int | None,
    sucursal_origen_id: int | None,
    estado: str,
    en_devolucion: bool,
) -> int | None:
    """Dónde se puede retirar el paquete, o `None` si no se retira en sucursal.

    - Devolución: en la sucursal de origen, y lo retira el remitente.
    - Envío a sucursal: en la sucursal que eligió el cliente.
    - Envío a domicilio que agotó las visitas: en la sucursal donde quedó esperando.
    """
    if en_devolucion:
        return sucursal_origen_id
    if (tipo_entrega or "").strip().lower() == "sucursal":
        return sucursal_destino_id
    if estado == E.LISTO_PARA_RETIRO.value:
        return sucursal_actual_id
    return None


def estado_al_llegar(
    *,
    tipo_entrega: str | None,
    sucursal_destino_id: int | None,
    sucursal_origen_id: int | None,
    en_devolucion: bool,
    sucursal_llegada_id: int,
) -> str:
    """Estado de un paquete verificado al descargarlo en una sucursal.

    Queda listo para retirar si esa es su sucursal de retiro (la elegida por el
    cliente o, en una devolución, la de origen). Si no, espera el siguiente
    tramo: el reparto a domicilio desde esa sucursal.
    """
    if en_devolucion:
        return E.LISTO_PARA_RETIRO.value if sucursal_llegada_id == sucursal_origen_id else E.EN_DEVOLUCION.value
    if (tipo_entrega or "").strip().lower() == "sucursal" and sucursal_destino_id == sucursal_llegada_id:
        return E.LISTO_PARA_RETIRO.value
    return E.EN_SUCURSAL_DESTINO.value


def agoto_visitas(visitas_fallidas: int, maximo: int) -> bool:
    """Tras la última visita sin éxito el paquete deja de salir a reparto y espera retiro."""
    return visitas_fallidas >= maximo


def texto_visita(numero: int, maximo: int) -> str:
    """«1.ª de 2 visitas» para el repartidor y el seguimiento."""
    return f"{numero}.ª de {maximo} visitas"
