from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.sucursales import SucursalData
from app.domain.constants.estados_logistica import TipoRetiroEnum


class DocumentoPresentadoDTO(BaseModel):
    """Información del documento de identidad presentado físicamente."""

    model_config = ConfigDict(from_attributes=True)

    tipo: str = Field(..., description="Tipo de documento (ej. 'DNI', 'PASAPORTE', 'LC', 'LE')", min_length=1, max_length=20)
    numero: str = Field(..., description="Número de documento de la persona que retira", min_length=1, max_length=20)


class TerceroAutorizadoDTO(BaseModel):
    """Datos de la persona autorizada a retirar y verificación de recaudos exigidos."""

    model_config = ConfigDict(from_attributes=True)

    nombre_completo: str = Field(..., description="Nombre completo de la persona autorizada", min_length=2, max_length=150)
    documento: str = Field(..., description="Número de documento de la persona autorizada", min_length=1, max_length=20)
    posee_copia_dni_titular: bool = Field(
        ...,
        description="Indica si presentó copia física o digital del documento del destinatario titular",
    )
    posee_nota_autorizacion: bool = Field(
        ...,
        description="Indica si presentó la nota o formulario de autorización firmado por el titular",
    )


class RegistrarRetiroRequest(BaseModel):
    """Cuerpo de la solicitud para asentar el retiro físico de un paquete en sucursal (HU13)."""

    model_config = ConfigDict(from_attributes=True)

    tipo_retiro: Literal["TITULAR", "TERCERO_AUTORIZADO"] = Field(
        ...,
        description="Modalidad de retiro: 'TITULAR' (destinatario en persona) o 'TERCERO_AUTORIZADO'",
    )
    documento_presentado: DocumentoPresentadoDTO = Field(
        ...,
        description="Documento presentado por quien realiza el retiro",
    )
    destinatario_mayor_16: bool = Field(
        ...,
        description="Validación de que el destinatario titular es mayor o igual a 16 años",
    )
    tercero_autorizado: Optional[TerceroAutorizadoDTO] = Field(
        None,
        description="Requerido obligatoriamente si tipo_retiro es 'TERCERO_AUTORIZADO'",
    )
    observaciones: Optional[str] = Field(
        None,
        description="Observaciones operativas del personal de sucursal",
        max_length=500,
    )


class DestinatarioRetiroInfo(BaseModel):
    """Datos de contacto del destinatario para validación de identidad."""

    model_config = ConfigDict(from_attributes=True)

    nombre: str
    telefono: str
    email: str


class RequisitosRetiroInfo(BaseModel):
    """Requisitos documentales normativos según la modalidad de retiro."""

    titular: str = "Presentar documento de identidad original y acreditar ser mayor de 16 años."
    tercero_autorizado: str = (
        "Presentar documento de identidad propio, copia del documento del titular "
        "y constancia/formulario de autorización de retiro firmada por el destinatario."
    )


class ValidarRetiroData(BaseModel):
    """Información completa de verificación previa al retiro de un paquete."""

    model_config = ConfigDict(from_attributes=True)

    paquete_id: UUID
    numero_paquete: str
    descripcion: str
    peso_kg: float
    estado_actual: str
    disponible_para_retiro: bool
    motivo_no_disponible: Optional[str] = None
    tipo_entrega: str
    sucursal_destino: Optional[SucursalData] = None
    sucursal_actual: Optional[SucursalData] = None
    datos_destinatario: DestinatarioRetiroInfo
    requisitos_retiro: RequisitosRetiroInfo = Field(default_factory=RequisitosRetiroInfo)


class ValidarRetiroResponse(BaseModel):
    """Respuesta estándar para la consulta de validación de retiro."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "success"
    data: ValidarRetiroData


class RetiroRegistradoData(BaseModel):
    """Datos confirmados tras el registro exitoso del retiro."""

    model_config = ConfigDict(from_attributes=True)

    paquete_id: UUID
    numero_paquete: str
    estado: str
    tipo_retiro: str
    receptor_nombre: str
    receptor_documento: str
    es_autorizado: bool
    usuario_administrativo_id: UUID
    usuario_administrativo_nombre: str
    fecha_hora_entrega: datetime
    sucursal_id: Optional[int] = None
    observaciones: Optional[str] = None


class RegistrarRetiroResponse(BaseModel):
    """Respuesta estándar tras registrar el retiro de un paquete."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "success"
    message: str = "Retiro del paquete registrado exitosamente en sucursal."
    data: RetiroRegistradoData
