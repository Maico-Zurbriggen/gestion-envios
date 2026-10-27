from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.contracts.common import ApiModel


class DatosNotificacionEnvio(BaseModel):
    """Payload de datos necesarios para disparar las notificaciones de seguimiento (HU05)."""

    model_config = ConfigDict(from_attributes=True)

    envio_id: UUID
    token_seguimiento: str
    remitente_nombre: str
    remitente_email: str
    remitente_telefono: str
    destinatario_nombre: str
    destinatario_email: str
    destinatario_telefono: str
    numeros_paquetes: list[str]


class NotificacionItemData(ApiModel):
    """Un intento de notificación por canal y destinatario, tal como quedó auditado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    motivo: Literal["NUEVO_ENVIO", "VISITA_FALLIDA"]
    canal: Literal["EMAIL", "WHATSAPP"]
    destinatario_tipo: Literal["REMITENTE", "DESTINATARIO"]
    destino: str
    estado: Literal["PENDIENTE", "ENVIADO", "FALLIDO"]
    error_detalle: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificacionesEnvioData(ApiModel):
    token_seguimiento: str
    notificaciones: list[NotificacionItemData]


class NotificacionesEnvioResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: NotificacionesEnvioData
