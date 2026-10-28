"""Contratos de la personalización de correos a clientes."""

from datetime import datetime

from pydantic import EmailStr, Field

from app.contracts.common import ApiModel


class VariablePlantillaData(ApiModel):
    nombre: str
    descripcion: str


class TextosPlantillaData(ApiModel):
    asunto: str
    titulo: str
    mensaje: str
    texto_boton: str
    pie: str


class PlantillaCorreoData(TextosPlantillaData):
    clave: str
    nombre: str
    descripcion: str
    variables: list[VariablePlantillaData]
    personalizada: bool
    updated_at: datetime | None = None
    de_fabrica: TextosPlantillaData


class ConfiguracionCorreoData(ApiModel):
    nombre_marca: str
    firma: str
    telefono_contacto: str
    email_contacto: str
    sitio_web: str
    mensaje_legal: str
    updated_at: datetime | None = None


class PlantillasCorreoData(ApiModel):
    plantillas: list[PlantillaCorreoData]
    configuracion: ConfiguracionCorreoData


class PlantillasCorreoResponse(ApiModel):
    status: str = "success"
    message: str = "Plantillas obtenidas correctamente."
    data: PlantillasCorreoData


class GuardarPlantillaRequest(ApiModel):
    asunto: str = Field(..., max_length=200)
    titulo: str = Field(..., max_length=150)
    mensaje: str = Field(..., max_length=2000)
    texto_boton: str = Field(..., max_length=60)
    pie: str = Field("", max_length=600)


class PlantillaCorreoResponse(ApiModel):
    status: str = "success"
    message: str = "Plantilla guardada."
    data: PlantillaCorreoData


class GuardarConfiguracionRequest(ApiModel):
    nombre_marca: str = Field(..., max_length=100)
    firma: str = Field("", max_length=300)
    telefono_contacto: str = Field("", max_length=40)
    email_contacto: str = Field("", max_length=150)
    sitio_web: str = Field("", max_length=200)
    mensaje_legal: str = Field("", max_length=600)


class ConfiguracionCorreoResponse(ApiModel):
    status: str = "success"
    message: str = "Datos de la empresa guardados."
    data: ConfiguracionCorreoData


class VistaPreviaRequest(ApiModel):
    """Textos sin guardar para previsualizar; los que falten salen de la plantilla vigente."""

    asunto: str | None = Field(None, max_length=200)
    titulo: str | None = Field(None, max_length=150)
    mensaje: str | None = Field(None, max_length=2000)
    texto_boton: str | None = Field(None, max_length=60)
    pie: str | None = Field(None, max_length=600)


class VistaPreviaData(ApiModel):
    asunto: str
    texto: str
    html: str


class VistaPreviaResponse(ApiModel):
    status: str = "success"
    message: str = "Vista previa generada con datos de ejemplo."
    data: VistaPreviaData


class EnviarPruebaRequest(VistaPreviaRequest):
    email: EmailStr


class EnviarPruebaData(ApiModel):
    enviado: bool
    destino: str
    detalle: str | None = None


class EnviarPruebaResponse(ApiModel):
    status: str = "success"
    message: str = "Correo de prueba enviado."
    data: EnviarPruebaData
