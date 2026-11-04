"""Contratos de request/response de la sección de preguntas frecuentes (HU08)."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.contracts.common import ApiModel
from app.domain.rules.preguntas_frecuentes_rules import LONGITUD_MAXIMA_CATEGORIA

# --- Vista pública ---


class PreguntaFrecuenteData(ApiModel):
    """Una pregunta frecuente tal como se muestra al público.

    `categoria` nunca viene vacía: las preguntas sin categoría se agrupan en
    "General" para que la vista pública no tenga que resolver ese caso.
    """

    id: int
    categoria: str
    pregunta: str
    respuesta: str
    orden: int


class CategoriaPreguntasData(ApiModel):
    """Una categoría de la sección, con cuántas preguntas publicadas tiene."""

    nombre: str
    cantidad: int


class ListadoPreguntasFrecuentesData(ApiModel):
    """Resultado de la consulta pública.

    `categorias` siempre lista **todas** las categorías publicadas (aunque se
    haya filtrado por una), para que el frontend pueda dibujar los filtros sin
    una segunda consulta. `preguntas` y `total` sí respetan los filtros.
    """

    total: int
    categorias: list[CategoriaPreguntasData]
    preguntas: list[PreguntaFrecuenteData]


class ListarPreguntasFrecuentesResponse(ApiModel):
    """Respuesta pública de la sección de preguntas frecuentes (HU08)."""

    status: str = "success"
    data: ListadoPreguntasFrecuentesData


# --- Administración del contenido ---


class PreguntaFrecuenteAdminData(ApiModel):
    """Vista completa para quien administra el contenido, incluidas las no publicadas."""

    id: int
    categoria: str | None
    pregunta: str
    respuesta: str
    orden: int
    publicada: bool
    created_at: datetime
    updated_at: datetime


class ListarPreguntasFrecuentesAdminResponse(ApiModel):
    status: str = "success"
    data: list[PreguntaFrecuenteAdminData]


class PreguntaFrecuenteAdminResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: PreguntaFrecuenteAdminData


class EliminarPreguntaFrecuenteResponse(ApiModel):
    status: str = "success"
    message: str = "Pregunta frecuente eliminada correctamente."


class CrearPreguntaFrecuenteRequest(ApiModel):
    """Alta de una pregunta frecuente desde la administración."""

    categoria: str | None = Field(
        None,
        max_length=LONGITUD_MAXIMA_CATEGORIA,
        description="Sección donde se agrupa la pregunta. Si se omite, se muestra en 'General'.",
        examples=["Retiro en sucursal"],
    )
    pregunta: str = Field(..., min_length=5, max_length=255, examples=["¿Qué necesito para retirar mi paquete?"])
    respuesta: str = Field(..., min_length=10, max_length=5000)
    orden: int = Field(0, ge=0, le=10000, description="Posición en la vista pública (menor = primero).")
    publicada: bool = Field(True, description="Si es `false`, la pregunta queda guardada pero no se muestra.")

    @field_validator("pregunta", "respuesta")
    @classmethod
    def validar_texto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El texto no puede estar vacío.")
        return v


class ActualizarPreguntaFrecuenteRequest(ApiModel):
    """Modificación parcial: solo se cambian los campos enviados.

    Para quitarle la categoría a una pregunta se envía `"categoria": null`
    explícitamente; omitir el campo la deja como estaba.
    """

    categoria: str | None = Field(None, max_length=LONGITUD_MAXIMA_CATEGORIA)
    pregunta: str | None = Field(None, min_length=5, max_length=255)
    respuesta: str | None = Field(None, min_length=10, max_length=5000)
    orden: int | None = Field(None, ge=0, le=10000)
    publicada: bool | None = None

    @field_validator("pregunta", "respuesta")
    @classmethod
    def validar_texto_no_vacio(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("El texto no puede estar vacío.")
        return v

    @model_validator(mode="after")
    def validar_algun_campo(self) -> "ActualizarPreguntaFrecuenteRequest":
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un campo para modificar.")
        for campo in ("pregunta", "respuesta", "orden", "publicada"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"El campo '{campo}' no puede ser nulo.")
        return self
