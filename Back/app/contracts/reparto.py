from datetime import UTC, date, datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.contracts.common import ApiModel
from app.domain.rules.reparto_rules import MAX_FIRMA_BYTES, decodificar_firma_png


class UbicacionRequest(ApiModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    latitud: float = Field(..., ge=-90, le=90, strict=True)
    longitud: float = Field(..., ge=-180, le=180, strict=True)


class OptimizarRecorridoRequest(ApiModel):
    """Ubicación actual del repartidor (opcional): desde ahí se ordena lo que falta."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)


class UbicacionData(UbicacionRequest):
    actualizado_at: datetime

    @field_validator("actualizado_at")
    @classmethod
    def fecha_utc(cls, valor: datetime) -> datetime:
        return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


class UbicacionResponse(ApiModel):
    status: str = "success"
    data: UbicacionData | None = None
    paquetes_actualizados: list[UUID] = Field(default_factory=list)


class RegistrarEntregaRequest(ApiModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    operacion_id: UUID = Field(..., description="UUID generado una vez por operación; reutilizar al reintentar.")
    receptor_nombre: str = Field(..., min_length=2, max_length=150)
    receptor_documento: str = Field(..., min_length=1, max_length=20)
    receptor_fecha_nacimiento: date
    es_autorizado: bool = Field(..., strict=True)
    firma_base64: str = Field(..., min_length=1, max_length=4 * ((MAX_FIRMA_BYTES + 2) // 3))

    @field_validator("firma_base64")
    @classmethod
    def validar_firma(cls, valor: str) -> str:
        decodificar_firma_png(valor)
        return valor


class RegistrarVisitaFallidaRequest(ApiModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    operacion_id: UUID
    motivo_fallo: str = Field(..., min_length=3, max_length=255)


class EventoEntregaData(ApiModel):
    evento_id: UUID
    paquete_id: UUID
    recorrido_id: UUID
    resultado: str
    receptor_nombre: str | None = None
    receptor_documento: str | None = None
    es_autorizado: bool = False
    firma_disponible: bool
    motivo_fallo: str | None = None
    fecha_hora: datetime

    @field_validator("fecha_hora")
    @classmethod
    def fecha_utc(cls, valor: datetime) -> datetime:
        return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


class EventoEntregaResponse(ApiModel):
    status: str = "success"
    data: EventoEntregaData


class ContactoEntregaData(ApiModel):
    paquete_id: UUID
    destinatario_nombre: str
    telefono: str | None
    telefono_disponible: bool


class ContactoEntregaResponse(ApiModel):
    status: str = "success"
    data: ContactoEntregaData
