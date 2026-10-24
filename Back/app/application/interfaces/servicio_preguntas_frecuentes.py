from typing import Protocol

from app.contracts.preguntas_frecuentes import (
    ActualizarPreguntaFrecuenteRequest,
    CrearPreguntaFrecuenteRequest,
    EliminarPreguntaFrecuenteResponse,
    ListarPreguntasFrecuentesAdminResponse,
    ListarPreguntasFrecuentesResponse,
    PreguntaFrecuenteAdminResponse,
)


class IServicioPreguntasFrecuentes(Protocol):
    """Protocolo del servicio de la sección de preguntas frecuentes (HU08)."""

    async def listar_publicas(
        self,
        categoria: str | None = None,
        busqueda: str | None = None,
    ) -> ListarPreguntasFrecuentesResponse:
        """Contenido publicado de la sección, sin autenticación (HU08 Escenario 1)."""
        ...

    async def listar_administracion(self) -> ListarPreguntasFrecuentesAdminResponse:
        """Todo el contenido, incluidas las preguntas no publicadas."""
        ...

    async def obtener(self, id: int) -> PreguntaFrecuenteAdminResponse: ...

    async def crear(self, datos: CrearPreguntaFrecuenteRequest) -> PreguntaFrecuenteAdminResponse: ...

    async def actualizar(
        self,
        id: int,
        datos: ActualizarPreguntaFrecuenteRequest,
    ) -> PreguntaFrecuenteAdminResponse: ...

    async def eliminar(self, id: int) -> EliminarPreguntaFrecuenteResponse: ...
