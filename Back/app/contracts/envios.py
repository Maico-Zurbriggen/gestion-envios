from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.contracts.common import ApiModel
from app.contracts.sucursales import SucursalData


class PaqueteRequest(ApiModel):
    descripcion: str = Field(..., min_length=2, max_length=255, examples=["Ropa y calzado"])
    peso_kg: float = Field(..., gt=0, examples=[3.5])
    largo_cm: float = Field(..., gt=0, examples=[40])
    ancho_cm: float = Field(..., gt=0, examples=[30])
    alto_cm: float = Field(..., gt=0, examples=[20])
    observaciones: str | None = Field(None, max_length=500)


class CrearEnvioRequest(ApiModel):
    # Remitente
    remitente_nombre: str = Field(..., min_length=2, max_length=150)
    remitente_documento: str = Field(..., min_length=6, max_length=20)
    remitente_telefono: str = Field(..., min_length=6, max_length=30)
    remitente_email: EmailStr

    # Destinatario
    destinatario_nombre: str = Field(..., min_length=2, max_length=150)
    destinatario_telefono: str = Field(..., min_length=6, max_length=30)
    destinatario_email: EmailStr

    # Entrega
    tipo_entrega: str = Field(..., description="'domicilio' o 'sucursal'")
    provincia_destino: str | None = None
    ciudad_destino: str | None = None
    direccion_destino: str | None = None
    latitud_destino: float | None = None
    longitud_destino: float | None = None
    sucursal_destino_id: int | None = None

    terminos_aceptados: bool

    paquetes: list[PaqueteRequest] = Field(..., min_length=1)

    @field_validator("tipo_entrega")
    @classmethod
    def validar_tipo_entrega(cls, v: str) -> str:
        if v not in ("domicilio", "sucursal"):
            raise ValueError("tipo_entrega debe ser 'domicilio' o 'sucursal'.")
        return v

    @field_validator("remitente_documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El documento debe contener solo dígitos.")
        return v

    @model_validator(mode="after")
    def validar_terminos_y_destino(self) -> "CrearEnvioRequest":
        if not self.terminos_aceptados:
            raise ValueError("Debe aceptar los términos y condiciones para registrar el envío.")

        if self.tipo_entrega == "sucursal" and not self.sucursal_destino_id:
            raise ValueError("Debe indicar sucursal_destino_id para tipo_entrega='sucursal'.")

        if self.tipo_entrega == "domicilio" and not (
            self.provincia_destino and self.ciudad_destino and self.direccion_destino
        ):
            raise ValueError(
                "Debe indicar provincia_destino, ciudad_destino y direccion_destino para tipo_entrega='domicilio'."
            )

        return self


class PaqueteCreadoData(ApiModel):
    id: UUID
    numero_paquete: str
    descripcion: str
    peso_kg: float
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    observaciones: str | None
    estado: str


class EnvioCreadoData(ApiModel):
    id: UUID
    token_seguimiento: str
    remitente_nombre: str
    remitente_documento: str
    remitente_telefono: str
    remitente_email: str
    destinatario_nombre: str
    destinatario_telefono: str
    destinatario_email: str
    tipo_entrega: str
    provincia_destino: str | None
    ciudad_destino: str | None
    direccion_destino: str | None
    latitud_destino: float | None
    longitud_destino: float | None
    sucursal_destino: SucursalData | None = None
    paquetes: list[PaqueteCreadoData]
    created_at: datetime


class CrearEnvioResponse(ApiModel):
    status: str = "success"
    message: str = "Envío registrado correctamente."
    data: EnvioCreadoData
