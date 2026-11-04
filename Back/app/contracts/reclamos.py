"""Contratos de request/response de los reclamos iniciados desde la vista pública (HU07)."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.contracts.common import ApiModel
from app.domain.constants.estados_logistica import EstadoReclamoEnum
from app.domain.rules.reclamo_rules import (
    DESCRIPCIONES_TIPO_RECLAMO,
    es_tipo_reclamo_valido,
    normalizar_tipo_reclamo,
)

# --- Vista pública (con el token de seguimiento) ---


class TipoReclamoData(ApiModel):
    codigo: str
    descripcion: str


class PaqueteReclamableData(ApiModel):
    """Paquete del envío que se puede señalar como afectado por el reclamo."""

    numero_paquete: str
    descripcion: str
    estado: str


class ReclamoPublicoData(ApiModel):
    """Reclamo tal como se muestra en la vista pública del token.

    No incluye los datos de contacto de quien reclamó: el endpoint es público
    y cualquiera con el token (remitente o destinatario) puede consultarlo.
    """

    id: UUID
    numero_paquete: str | None = None
    tipo: str
    estado: str
    descripcion: str
    resolucion: str | None = None
    fecha_creacion: datetime
    ultima_actualizacion: datetime


class InicioReclamoData(ApiModel):
    """Lo que necesita la vista pública para habilitar el inicio de un reclamo.

    `puede_iniciar` es `False` solo cuando el envío alcanzó el tope de
    reclamos activos; en ese caso `motivo_no_habilitado` explica por qué.
    """

    token_seguimiento: str
    puede_iniciar: bool
    motivo_no_habilitado: str | None = None
    max_reclamos_activos: int
    tipos_reclamo: list[TipoReclamoData]
    paquetes: list[PaqueteReclamableData]
    reclamos: list[ReclamoPublicoData]


class InicioReclamoResponse(ApiModel):
    status: str = "success"
    data: InicioReclamoData


class CrearReclamoRequest(ApiModel):
    """Alta de un reclamo para el envío consultado con el token."""

    tipo: str = Field(..., description="'DEMORA', 'DANIO', 'EXTRAVIO' u 'OTRO'.", examples=["DEMORA"])
    descripcion: str = Field(..., min_length=20, max_length=2000)
    numero_paquete: str | None = Field(
        None,
        max_length=30,
        description="Paquete afectado (`PAQ-XXXXXXXXXX`). Si se omite, el reclamo es por el envío completo.",
    )
    contacto_nombre: str = Field(..., min_length=2, max_length=150)
    contacto_email: EmailStr | None = None
    contacto_telefono: str | None = Field(None, max_length=30)

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if not es_tipo_reclamo_valido(v):
            raise ValueError(
                f"Tipo de reclamo inválido. Valores aceptados: {', '.join(DESCRIPCIONES_TIPO_RECLAMO)}."
            )
        return normalizar_tipo_reclamo(v)

    @field_validator("descripcion", "contacto_nombre")
    @classmethod
    def recortar_texto(cls, v: str) -> str:
        return v.strip()

    @field_validator("numero_paquete", "contacto_telefono")
    @classmethod
    def vaciar_opcionales(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def validar_longitudes_recortadas(self) -> "CrearReclamoRequest":
        if len(self.descripcion) < 20:
            raise ValueError("La descripción debe tener al menos 20 caracteres.")
        if len(self.contacto_nombre) < 2:
            raise ValueError("Debe indicar el nombre de contacto.")
        return self


class CrearReclamoResponse(ApiModel):
    status: str = "success"
    message: str = "Reclamo registrado. Vas a poder seguir su estado con tu código de seguimiento."
    data: ReclamoPublicoData


# --- Gestión interna ---


class ReclamoAdminData(ApiModel):
    """Reclamo completo para el personal que lo gestiona, con datos de contacto."""

    id: UUID
    envio_id: UUID
    token_seguimiento: str
    remitente_nombre: str
    destinatario_nombre: str
    numero_paquete: str | None = None
    tipo: str
    descripcion: str
    contacto_nombre: str
    contacto_email: str | None = None
    contacto_telefono: str | None = None
    estado: str
    resolucion: str | None = None
    usuario_resolucion_id: UUID | None = None
    usuario_resolucion_nombre: str | None = None
    created_at: datetime
    updated_at: datetime


class ListarReclamosAdminResponse(ApiModel):
    status: str = "success"
    total: int
    data: list[ReclamoAdminData]


class ReclamoAdminResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: ReclamoAdminData


class ActualizarEstadoReclamoRequest(ApiModel):
    """Cambio de estado del reclamo. `resolucion` es obligatoria para cerrarlo."""

    estado: str = Field(
        ...,
        description="'EN_REVISION', 'RESUELTO' o 'RECHAZADO'.",
        examples=[EstadoReclamoEnum.RESUELTO.value],
    )
    resolucion: str | None = Field(None, max_length=2000)

    @field_validator("estado")
    @classmethod
    def normalizar_estado(cls, v: str) -> str:
        return v.strip().upper()
