from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class NotificacionItemData(BaseModel):
    """Representación de un registro de auditoría de notificación."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    envio_id: UUID
    canal: str
    destinatario_tipo: str
    destino: str
    estado: str
    proveedor_mensaje_id: str | None = None
    error_detalle: str | None = None
    created_at: datetime
