"""Contratos del control de descarga en la sucursal de destino."""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.contracts.common import ApiModel


class RecorridoEntranteData(ApiModel):
    recorrido_id: UUID
    fecha: date
    estado: str
    repartidor_nombre: str
    sucursal_origen: str
    esperados: int
    verificados: int
    control_id: UUID | None = None
    control_estado: str | None = None


class RecorridosEntrantesResponse(ApiModel):
    status: str = "success"
    data: list[RecorridoEntranteData]


class PaqueteEsperadoData(ApiModel):
    paquete_id: UUID
    numero_paquete: str
    descripcion: str
    destinatario_nombre: str
    tipo_entrega: str
    estado: str
    estado_etiqueta: str
    verificado: bool
    verificado_at: datetime | None = None
    verificado_por: str | None = None


class LecturaDescargaData(ApiModel):
    codigo: str
    resultado: str
    detalle: str | None = None
    usuario_nombre: str | None = None
    created_at: datetime


class SucursalDescargaData(ApiModel):
    id: int
    nombre: str


class RecorridoDescargaData(ApiModel):
    id: UUID
    fecha: date
    estado: str
    repartidor_nombre: str
    sucursal_origen: str


class ControlDescargaData(ApiModel):
    id: UUID
    estado: str
    recorrido: RecorridoDescargaData
    sucursal: SucursalDescargaData
    esperados: list[PaqueteEsperadoData]
    sobrantes: list[LecturaDescargaData]
    total_esperados: int
    verificados: int
    faltantes: int
    resumen: str
    iniciado_por: str | None = None
    created_at: datetime
    cerrado_por: str | None = None
    cerrado_at: datetime | None = None
    observaciones: str | None = None


class ControlDescargaResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: ControlDescargaData


class IniciarControlRequest(ApiModel):
    recorrido_id: UUID
    sucursal_id: int = Field(..., ge=1)


class RegistrarLecturaRequest(ApiModel):
    codigo: str = Field(..., min_length=1, max_length=40)


class ResultadoLecturaData(ApiModel):
    codigo: str
    resultado: str = Field(..., description="CORRECTO, SOBRANTE o DESCONOCIDO.")
    repetida: bool = False
    mensaje: str
    control: ControlDescargaData


class ResultadoLecturaResponse(ApiModel):
    status: str = "success"
    data: ResultadoLecturaData


class CerrarControlRequest(ApiModel):
    observaciones: str | None = Field(None, max_length=1000)
