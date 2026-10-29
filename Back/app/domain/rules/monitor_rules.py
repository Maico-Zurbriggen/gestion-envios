"""Reglas puras del monitor de envíos: agrupación de estados, etiquetas internas
y armado de la línea de tiempo de trazabilidad de un paquete."""

from datetime import UTC, datetime, timedelta, timezone

from app.domain.constants.estados_logistica import EstadoPaqueteEnum as E

ESTADO_INICIAL_LITERAL = "Pendiente"
"""HU03 crea los paquetes con este literal (no con el valor del enum)."""

GRUPOS_ESTADO: dict[str, tuple[str, ...]] = {
    "PENDIENTES": (ESTADO_INICIAL_LITERAL, E.PENDIENTE.value),
    "EN_DEPOSITO": (E.EN_SUCURSAL_ORIGEN.value, E.EN_SUCURSAL_DESTINO.value, E.EN_SUCURSAL.value),
    "EN_CAMINO": (E.EN_TRANSITO.value, E.EN_REPARTO.value),
    "PARA_RETIRAR": (E.LISTO_PARA_RETIRO.value,),
    "NO_ENTREGADOS": (E.ENTREGA_FALLIDA.value,),
    "ENTREGADOS": (E.ENTREGADO.value, E.RETIRADO.value, E.ENTREGADO_EN_SUCURSAL.value),
    "DEVOLUCIONES": (E.EN_DEVOLUCION.value, E.DEVUELTO.value),
    "VENCIDOS": (E.VENCIDO.value,),
}
"""Grupos del monitor, en el orden en que avanza un paquete."""

FILTROS_ESPECIALES = ("CON_PROBLEMAS", "SIN_RECORRIDO", "CON_RECLAMO")
"""Filtros que no dependen solo del estado: fallidos, sin recorrido o reclamos en curso."""


ETIQUETAS_ESTADO: dict[str, str] = {
    ESTADO_INICIAL_LITERAL: "Pendiente de ingreso",
    E.PENDIENTE.value: "Pendiente de ingreso",
    E.EN_SUCURSAL_ORIGEN.value: "En terminal de origen",
    E.EN_TRANSITO.value: "En tránsito",
    E.EN_SUCURSAL_DESTINO.value: "En sucursal de destino",
    E.LISTO_PARA_RETIRO.value: "Listo para retirar",
    E.EN_SUCURSAL.value: "En sucursal",
    E.EN_REPARTO.value: "En reparto",
    E.ENTREGADO.value: "Entregado a domicilio",
    E.ENTREGA_FALLIDA.value: "Visita fallida",
    E.RETIRADO.value: "Retirado",
    E.ENTREGADO_EN_SUCURSAL.value: "Retirado en sucursal",
    E.EN_DEVOLUCION.value: "En devolución",
    E.DEVUELTO.value: "Devuelto al remitente",
    E.VENCIDO.value: "Registro vencido",
}

ESTADOS_DE_ENTREGA = frozenset(
    {E.ENTREGADO.value, E.ENTREGA_FALLIDA.value, E.RETIRADO.value, E.ENTREGADO_EN_SUCURSAL.value}
)
"""Estados que también quedan registrados como evento de entrega o retiro."""

ESTADOS_RECLAMO_EN_CURSO = ("ABIERTO", "EN_REVISION")

ZONA_HORARIA_LOCAL = timezone(timedelta(hours=-3))
"""Argentina no tiene horario de verano: el día operativo se corta a las 00:00 UTC-3."""


def grupo_de_estado(estado: str) -> str:
    for grupo, estados in GRUPOS_ESTADO.items():
        if estado in estados:
            return grupo
    return "OTROS"


def grupo_de_paquete(estado: str, en_devolucion: bool) -> str:
    """Como `grupo_de_estado`, pero un paquete que vuelve al remitente es siempre una devolución,
    aunque esté esperando en la sucursal de origen («Listo para retirar»)."""
    return "DEVOLUCIONES" if en_devolucion else grupo_de_estado(estado)


def filtro_devolucion(grupo: str) -> bool | None:
    """Cómo filtrar `en_devolucion` en un grupo: incluirlas, excluirlas o no filtrar."""
    return {"DEVOLUCIONES": True, "PARA_RETIRAR": False}.get(grupo)


def etiqueta_estado(estado: str) -> str:
    return ETIQUETAS_ESTADO.get(estado, estado.replace("_", " ").capitalize())


def estados_de_grupo(grupo: str) -> tuple[str, ...] | None:
    """Estados que abarca un grupo; `None` si no es un grupo de estados."""
    return GRUPOS_ESTADO.get(grupo)


def inicio_del_dia_local(ahora: datetime) -> datetime:
    """00:00 del día en curso (hora argentina), expresado en UTC."""
    local = ahora.astimezone(ZONA_HORARIA_LOCAL)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def como_utc(momento: datetime) -> datetime:
    """SQLite devuelve fechas sin zona: se interpretan como UTC para poder ordenarlas."""
    return momento if momento.tzinfo else momento.replace(tzinfo=UTC)


def es_estado_duplicado_de_entrega(estado: str, momento: datetime, momentos_eventos: list[datetime]) -> bool:
    """Un cambio a ENTREGADO o ENTREGA_FALLIDA se registra a la vez en el historial
    y en `eventos_entrega`. La línea de tiempo muestra solo el evento, que tiene
    más datos (quién recibió, motivo, firma)."""
    if estado not in ESTADOS_DE_ENTREGA:
        return False
    instante = como_utc(momento)
    return any(abs((como_utc(otro) - instante).total_seconds()) <= 120 for otro in momentos_eventos)


def ocultar_documento(documento: str | None) -> str | None:
    """Muestra solo los últimos 3 dígitos del documento de quien recibió."""
    if not documento:
        return documento
    visibles = documento[-3:]
    return "•" * max(len(documento) - 3, 0) + visibles
