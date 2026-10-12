"""Contratos de request/response de la recepción de paquetes en terminal (HU06)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.contracts.common import ApiModel
from app.contracts.sucursales import SucursalData


class EnvioResumenRecepcion(ApiModel):
    """Datos del envío que el vendedor necesita ver al recibir el paquete.

    Incluye el contacto del remitente (quien está físicamente en el mostrador
    entregando el paquete) para poder contrastarlo con lo que declaró al
    precargar el envío. El endpoint está autenticado y restringido por rol, así
    que exponerlos acá no tiene el problema de privacidad de la vista pública
    de HU04.
    """

    envio_id: UUID
    token_seguimiento: str
    remitente_nombre: str
    remitente_documento: str
    remitente_telefono: str
    destinatario_nombre: str
    destinatario_telefono: str
    tipo_entrega: str
    destino: str = Field(
        ...,
        description="Destino ya armado como texto legible: domicilio completo o sucursal de retiro.",
    )
    sucursal_destino: SucursalData | None = None


class PaqueteEscaneadoData(ApiModel):
    """Identificación del paquete precargado a partir del código escaneado."""

    paquete_id: UUID
    numero_paquete: str
    descripcion: str
    peso_kg: float
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    observaciones: str | None = None
    estado_actual: str
    disponible_para_recepcion: bool
    motivo_no_disponible: str | None = None
    fecha_registro: datetime
    sucursal_actual: SucursalData | None = None
    envio: EnvioResumenRecepcion


class EscanearPaqueteResponse(ApiModel):
    """Respuesta de la identificación del paquete por código de barras (HU06)."""

    status: str = "success"
    data: PaqueteEscaneadoData


class RecepcionarPaqueteRequest(ApiModel):
    """Cuerpo para dejar el paquete registrado en la terminal como listo para su envío."""

    sucursal_id: int = Field(
        ...,
        description="Sucursal/terminal donde se recibe físicamente el paquete.",
        gt=0,
    )
    observaciones: Optional[str] = Field(
        None,
        description="Observaciones del vendedor sobre el estado en que recibió el paquete.",
        max_length=500,
    )


class PaqueteRecepcionadoData(ApiModel):
    """Confirmación del ingreso del paquete a la terminal."""

    paquete_id: UUID
    numero_paquete: str
    estado_anterior: str
    estado: str
    sucursal_id: int
    sucursal_nombre: str
    usuario_receptor_id: UUID
    usuario_receptor_nombre: str
    fecha_hora_recepcion: datetime
    observaciones: str | None = None
    token_seguimiento: str


class RecepcionarPaqueteResponse(ApiModel):
    """Respuesta estándar tras registrar la recepción en terminal (HU06)."""

    status: str = "success"
    message: str = "Paquete recibido y registrado en la terminal como listo para su envío."
    data: PaqueteRecepcionadoData
