"""Contratos de la generación, visualización y edición de recorridos de reparto (HU10)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ApiModel
from app.contracts.sucursales import SucursalData
from app.domain.constants.estados_logistica import TipoDistanciaEnum
from app.domain.rules.recorrido_rules import ORIENTACION_MAXIMA_GRADOS, ORIENTACION_MINIMA_GRADOS

TIPOS_DISTANCIA_VALIDOS = [t.value for t in TipoDistanciaEnum]


def _validar_tipo_distancia(valor: str) -> str:
    valor = valor.strip().upper()
    if valor not in TIPOS_DISTANCIA_VALIDOS:
        raise ValueError(f"Tipo de distancia inválido. Valores aceptados: {', '.join(TIPOS_DISTANCIA_VALIDOS)}.")
    return valor


# --- Requests ---


class GenerarRecorridosRequest(ApiModel):
    """Generación automática de los recorridos de una sucursal para una fecha (HU10 Escenario 1)."""

    sucursal_id: int = Field(..., gt=0, description="Sucursal de partida de los recorridos.")
    tipo_distancia: str = Field(..., description="'CORTA' (entregas en la ciudad) o 'LARGA' (entre sucursales).")
    fecha: date | None = Field(None, description="Día de reparto. Por defecto, hoy.")
    orientacion_calles_grados: float = Field(
        0.0,
        ge=ORIENTACION_MINIMA_GRADOS,
        lt=ORIENTACION_MAXIMA_GRADOS,
        description="Ángulo de la cuadrícula de calles respecto del norte (0 = calles norte-sur/este-oeste). "
        "Solo influye en los recorridos de corta distancia.",
    )
    repartidor_ids: list[UUID] | None = Field(
        None,
        max_length=100,
        description="Repartidores entre los que repartir. Por defecto, todos los disponibles de la sucursal.",
    )
    reemplazar_existentes: bool = Field(
        False,
        description="Si ya hay recorridos sin iniciar para esa sucursal, fecha y tipo, los descarta y genera de nuevo.",
    )

    @field_validator("tipo_distancia")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        return _validar_tipo_distancia(v)


class CrearRecorridoRequest(ApiModel):
    """Alta manual de un recorrido: el repartidor y los paquetes, en el orden de visita."""

    sucursal_id: int = Field(..., gt=0, description="Sucursal de partida.")
    tipo_distancia: str = Field(..., description="'CORTA' o 'LARGA'.")
    fecha: date | None = Field(None, description="Día de reparto. Por defecto, hoy.")
    repartidor_id: UUID
    paquetes: list[str] = Field(..., min_length=1, max_length=500, description="Códigos de paquete.")

    @field_validator("tipo_distancia")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        return _validar_tipo_distancia(v)


class ReemplazarPaquetesRecorridoRequest(ApiModel):
    """Composición y orden completos del recorrido tras una edición manual (HU10 Escenario 2).

    El orden de la lista es el orden de visita. Sirve para agregar, quitar y
    reordenar paquetes en una sola operación.
    """

    paquetes: list[str] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Números de paquete (`PAQ-XXXXXXXXXX`) o UUID, en el orden de visita.",
    )


class ReasignarRepartidorRequest(ApiModel):
    repartidor_id: UUID


class CompletarUbicacionPaqueteRequest(ApiModel):
    latitud: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(..., ge=-180, le=180, allow_inf_nan=False)


# --- Responses ---


class RepartidorRecorridoData(ApiModel):
    usuario_id: UUID
    nombre: str
    telefono: str


class PaqueteRecorridoData(ApiModel):
    """Paquete dentro de una parada. Incluye el contacto del destinatario porque
    el endpoint es interno y el repartidor lo necesita (HU12 Escenario 2)."""

    paquete_id: UUID
    numero_paquete: str
    orden: int
    descripcion: str
    peso_kg: float
    estado: str
    estado_en_recorrido: str
    token_seguimiento: str
    destinatario_nombre: str
    destinatario_telefono: str
    visitas_previas: int = Field(0, description="Visitas a domicilio sin éxito antes de este recorrido.")
    en_devolucion: bool = Field(False, description="Viaja de vuelta a la sucursal de origen.")


class ParadaRecorridoData(ApiModel):
    """Un punto a visitar: un domicilio (corta distancia) o una sucursal (larga)."""

    orden: int
    tipo_parada: str = Field(..., description="'DOMICILIO' o 'SUCURSAL'.")
    destino: str
    latitud: float | None = None
    longitud: float | None = None
    sucursal_destino: SucursalData | None = None
    paquetes: list[PaqueteRecorridoData]


class PuntoMapaData(ApiModel):
    latitud: float
    longitud: float


class RecorridoResumenData(ApiModel):
    id: UUID
    fecha: date
    tipo_distancia: str
    estado: str
    generado_automaticamente: bool
    sucursal_origen_id: int
    sucursal_origen_nombre: str
    repartidor: RepartidorRecorridoData
    cantidad_paradas: int
    cantidad_paquetes: int
    distancia_estimada_km: float | None = None
    duracion_estimada_min: int | None = None
    paquetes_entregados: int = 0
    paquetes_no_entregados: int = 0
    created_at: datetime
    updated_at: datetime


class ControlCargaResumenData(ApiModel):
    estado: str
    verificados: int
    esperados: int


class RecorridoDetalleData(RecorridoResumenData):
    """Recorrido listo para dibujar en un mapa.

    `trazado` es la secuencia de puntos en orden de visita (sucursal de
    partida, paradas con coordenadas y, en corta distancia, la vuelta a la
    sucursal). `paquetes_sin_ubicacion` cuenta paradas agregadas a mano cuyo
    destino no tiene coordenadas: figuran en `paradas` pero no en el trazado.
    """

    orientacion_calles_grados: float
    vuelve_a_sucursal: bool
    sucursal_origen: SucursalData
    paradas: list[ParadaRecorridoData]
    trazado: list[PuntoMapaData]
    paquetes_sin_ubicacion: int
    max_visitas: int = 2
    control_carga: ControlCargaResumenData | None = Field(
        None, description="Escaneo de lo que subió al vehículo en la sucursal de origen, si se hizo."
    )


class AlertaRecorridoData(ApiModel):
    """Paquete que quedó fuera de todo recorrido (HU10 Escenario 3)."""

    id: UUID
    paquete_id: UUID
    numero_paquete: str
    token_seguimiento: str
    destino: str
    motivo: str
    descripcion_motivo: str
    sucursal_actual_id: int | None = None
    recorrido_id: UUID | None = None
    resuelta: bool
    created_at: datetime
    resuelta_at: datetime | None = None


class ResumenGeneracionData(ApiModel):
    paquetes_pendientes: int = Field(..., description="Paquetes que esperaban un recorrido de este tipo.")
    paquetes_asignados: int
    paquetes_sin_recorrido: int
    repartidores_disponibles: int
    recorridos_generados: int
    recorridos_reemplazados: int


class GeneracionRecorridosData(ApiModel):
    sucursal_id: int
    fecha: date
    tipo_distancia: str
    orientacion_calles_grados: float
    resumen: ResumenGeneracionData
    recorridos: list[RecorridoDetalleData]
    alertas: list[AlertaRecorridoData]


class GenerarRecorridosResponse(ApiModel):
    status: str = "success"
    message: str
    data: GeneracionRecorridosData


class PaquetePendienteData(ApiModel):
    """Paquete listo en la sucursal que todavía no tiene recorrido."""

    paquete_id: UUID
    numero_paquete: str
    descripcion: str
    peso_kg: float
    destinatario_nombre: str
    destino: str
    token_seguimiento: str
    tiene_ubicacion: bool
    motivo: str | None = Field(None, description="Por qué no se puede planificar todavía (por ejemplo, sin ubicación).")
    visitas_previas: int = 0
    en_devolucion: bool = False


class EsperaSucursalData(ApiModel):
    sucursal_id: int
    nombre: str
    a_domicilio: int = Field(..., description="Esperan un recorrido de corta distancia.")
    entre_sucursales: int = Field(..., description="Esperan un recorrido de larga distancia.")
    sin_llegar: int = Field(0, description="Registrados para llevar a esta sucursal que todavía no llegaron.")


class ResumenEsperaData(ApiModel):
    sin_llegar: int = Field(..., description="Registrados que todavía no se recibieron (de las sucursales visibles).")
    sucursales: list[EsperaSucursalData] = Field(..., description="Solo las que tienen paquetes esperando.")


class ResumenEsperaResponse(ApiModel):
    status: str = "success"
    data: ResumenEsperaData


class PaquetesPendientesResponse(ApiModel):
    status: str = "success"
    total: int
    data: list[PaquetePendienteData]


class ListarRecorridosResponse(ApiModel):
    status: str = "success"
    total: int
    data: list[RecorridoResumenData]


class RecorridoResponse(ApiModel):
    """Detalle de un recorrido. Tras una edición, `alertas` trae los paquetes de
    la sucursal que siguen sin recorrido de ese tipo (HU10 Escenario 3)."""

    status: str = "success"
    message: str | None = None
    data: RecorridoDetalleData
    alertas: list[AlertaRecorridoData] = Field(default_factory=list)


class EliminarRecorridoResponse(ApiModel):
    status: str = "success"
    message: str = "Recorrido eliminado. Sus paquetes quedaron disponibles para otro recorrido."
    alertas: list[AlertaRecorridoData] = Field(default_factory=list)


class ListarAlertasRecorridoResponse(ApiModel):
    status: str = "success"
    total: int
    data: list[AlertaRecorridoData]


class AlertaRecorridoResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: AlertaRecorridoData
