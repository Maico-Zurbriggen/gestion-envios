"""Contratos del monitor de envíos: resumen, listado y trazabilidad de paquetes."""

from datetime import date, datetime
from uuid import UUID

from app.contracts.common import ApiModel


class SucursalOpcionData(ApiModel):
    id: int
    nombre: str


class ActividadHoyData(ApiModel):
    registrados: int
    ingresados: int
    entregados: int
    visitas_fallidas: int


class RecorridosHoyData(ApiModel):
    total: int
    generados: int
    en_curso: int
    finalizados: int
    repartidores_en_ruta: int


class ResumenMonitorData(ApiModel):
    total_paquetes: int
    total_envios: int
    por_grupo: dict[str, int]
    por_estado: dict[str, int]
    sin_recorrido: int
    faltantes: int
    con_reclamo: int
    con_problemas: int
    reclamos_abiertos: int
    notificaciones_fallidas: int
    hoy: ActividadHoyData
    recorridos_hoy: RecorridosHoyData
    sucursales: list[SucursalOpcionData]
    generado_at: datetime


class ResumenMonitorResponse(ApiModel):
    status: str = "success"
    data: ResumenMonitorData


class RecorridoAsignadoData(ApiModel):
    id: UUID
    fecha: date
    estado: str
    tipo_distancia: str
    repartidor_nombre: str
    orden: int
    estado_en_recorrido: str


class PaqueteMonitorData(ApiModel):
    id: UUID
    numero_paquete: str
    estado: str
    estado_etiqueta: str
    grupo: str
    descripcion: str
    peso_kg: float
    envio_id: UUID
    token_seguimiento: str
    remitente_nombre: str
    destinatario_nombre: str
    tipo_entrega: str
    destino: str
    sucursal_actual: str | None = None
    recorrido: RecorridoAsignadoData | None = None
    intentos_fallidos: int
    reclamos_en_curso: int
    sin_recorrido: bool
    faltante_en_descarga: bool = False
    created_at: datetime
    updated_at: datetime


class ListadoMonitorData(ApiModel):
    paquetes: list[PaqueteMonitorData]
    total: int
    pagina: int
    por_pagina: int
    paginas: int


class ListadoMonitorResponse(ApiModel):
    status: str = "success"
    data: ListadoMonitorData


class PersonaData(ApiModel):
    nombre: str
    documento: str | None = None
    telefono: str | None = None
    email: str | None = None


class EventoTrazaData(ApiModel):
    """Un hito de la línea de tiempo. `tipo` agrupa el origen: registro,
    estado, recorrido, entrega, alerta, reclamo o notificacion."""

    fecha: datetime
    tipo: str
    titulo: str
    detalle: str | None = None
    actor: str | None = None
    lugar: str | None = None
    tono: str = "neutral"
    latitud: float | None = None
    longitud: float | None = None
    evento_entrega_id: UUID | None = None
    con_firma: bool = False


class EntregaTrazaData(ApiModel):
    id: UUID
    fecha: datetime
    tipo_evento: str
    resultado: str
    receptor_nombre: str | None = None
    receptor_documento: str | None = None
    es_autorizado: bool
    motivo_fallo: str | None = None
    con_firma: bool
    registrado_por: str | None = None
    sucursal: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class AsignacionTrazaData(RecorridoAsignadoData):
    sucursal_origen: str
    asignado_at: datetime


class ReclamoTrazaData(ApiModel):
    id: UUID
    tipo: str
    estado: str
    descripcion: str
    resolucion: str | None = None
    contacto_nombre: str
    numero_paquete: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificacionTrazaData(ApiModel):
    canal: str
    destinatario_tipo: str
    destino: str
    estado: str
    motivo: str
    created_at: datetime
    updated_at: datetime


class PaqueteHermanoData(ApiModel):
    numero_paquete: str
    estado: str
    estado_etiqueta: str
    grupo: str


class TrazaPaqueteData(ApiModel):
    paquete: PaqueteMonitorData
    observaciones: str | None = None
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    remitente: PersonaData
    destinatario: PersonaData
    sucursal_destino: str | None = None
    direccion_destino: str | None = None
    latitud_destino: float | None = None
    longitud_destino: float | None = None
    paquetes_del_envio: list[PaqueteHermanoData]
    asignaciones: list[AsignacionTrazaData]
    entregas: list[EntregaTrazaData]
    reclamos: list[ReclamoTrazaData]
    notificaciones: list[NotificacionTrazaData]
    linea_de_tiempo: list[EventoTrazaData]


class TrazaPaqueteResponse(ApiModel):
    status: str = "success"
    data: TrazaPaqueteData
