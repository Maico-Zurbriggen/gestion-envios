from app.application.interfaces.repositorio_preguntas_frecuentes import IRepositorioPreguntasFrecuentes
from app.application.interfaces.servicio_preguntas_frecuentes import IServicioPreguntasFrecuentes
from app.contracts.preguntas_frecuentes import (
    ActualizarPreguntaFrecuenteRequest,
    CategoriaPreguntasData,
    CrearPreguntaFrecuenteRequest,
    EliminarPreguntaFrecuenteResponse,
    ListadoPreguntasFrecuentesData,
    ListarPreguntasFrecuentesAdminResponse,
    ListarPreguntasFrecuentesResponse,
    PreguntaFrecuenteAdminData,
    PreguntaFrecuenteAdminResponse,
    PreguntaFrecuenteData,
)
from app.core.exceptions import DuplicateEntryException, NotFoundException
from app.domain.rules.preguntas_frecuentes_rules import (
    categoria_visible,
    coincide_con_busqueda,
    es_pregunta_duplicada,
    misma_categoria,
    normalizar_categoria,
)
from app.infrastructure.db.models import PreguntaFrecuenteModel


class ServicioPreguntasFrecuentes(IServicioPreguntasFrecuentes):
    """Servicio de aplicación de la sección de preguntas frecuentes (HU08).

    Cubre el Escenario 1 de HU08 (consulta pública, sin iniciar sesión) y la
    administración del contenido, que es lo que justifica que viva en base y no
    hardcodeado en el frontend: se puede corregir una respuesta sin desplegar.
    """

    def __init__(self, repositorio_preguntas: IRepositorioPreguntasFrecuentes):
        self.repo_preguntas = repositorio_preguntas

    async def listar_publicas(
        self,
        categoria: str | None = None,
        busqueda: str | None = None,
    ) -> ListarPreguntasFrecuentesResponse:
        """Devuelve las preguntas publicadas, opcionalmente filtradas.

        Los filtros se aplican en memoria con las reglas de dominio, que ignoran
        tildes y mayúsculas (ver `preguntas_frecuentes_rules.py`).
        """
        publicadas = await self.repo_preguntas.listar(solo_publicadas=True)

        filtradas = [
            p
            for p in publicadas
            if (not categoria or not categoria.strip() or misma_categoria(p.categoria, categoria))
            and coincide_con_busqueda(busqueda, p.pregunta, p.respuesta, p.categoria)
        ]

        return ListarPreguntasFrecuentesResponse(
            data=ListadoPreguntasFrecuentesData(
                total=len(filtradas),
                categorias=self._resumir_categorias(publicadas),
                preguntas=[self._mapear_publica(p) for p in filtradas],
            )
        )

    async def listar_administracion(self) -> ListarPreguntasFrecuentesAdminResponse:
        preguntas = await self.repo_preguntas.listar(solo_publicadas=False)
        return ListarPreguntasFrecuentesAdminResponse(data=[self._mapear_admin(p) for p in preguntas])

    async def obtener(self, id: int) -> PreguntaFrecuenteAdminResponse:
        pregunta = await self._obtener_o_404(id)
        return PreguntaFrecuenteAdminResponse(data=self._mapear_admin(pregunta))

    async def crear(self, datos: CrearPreguntaFrecuenteRequest) -> PreguntaFrecuenteAdminResponse:
        await self._validar_no_duplicada(datos.pregunta)

        pregunta = PreguntaFrecuenteModel(
            categoria=normalizar_categoria(datos.categoria),
            pregunta=datos.pregunta,
            respuesta=datos.respuesta,
            orden=datos.orden,
            publicada=datos.publicada,
        )
        creada = await self.repo_preguntas.crear(pregunta)

        return PreguntaFrecuenteAdminResponse(
            message="Pregunta frecuente creada correctamente.",
            data=self._mapear_admin(creada),
        )

    async def actualizar(
        self,
        id: int,
        datos: ActualizarPreguntaFrecuenteRequest,
    ) -> PreguntaFrecuenteAdminResponse:
        pregunta = await self._obtener_o_404(id)
        campos = datos.model_fields_set

        if "pregunta" in campos and datos.pregunta is not None:
            await self._validar_no_duplicada(datos.pregunta, excluir_id=pregunta.id)
            pregunta.pregunta = datos.pregunta
        if "respuesta" in campos and datos.respuesta is not None:
            pregunta.respuesta = datos.respuesta
        if "categoria" in campos:
            pregunta.categoria = normalizar_categoria(datos.categoria)
        if "orden" in campos and datos.orden is not None:
            pregunta.orden = datos.orden
        if "publicada" in campos and datos.publicada is not None:
            pregunta.publicada = datos.publicada

        actualizada = await self.repo_preguntas.actualizar(pregunta)
        return PreguntaFrecuenteAdminResponse(
            message="Pregunta frecuente actualizada correctamente.",
            data=self._mapear_admin(actualizada),
        )

    async def eliminar(self, id: int) -> EliminarPreguntaFrecuenteResponse:
        pregunta = await self._obtener_o_404(id)
        await self.repo_preguntas.eliminar(pregunta)
        return EliminarPreguntaFrecuenteResponse()

    async def _obtener_o_404(self, id: int) -> PreguntaFrecuenteModel:
        pregunta = await self.repo_preguntas.obtener_por_id(id)
        if not pregunta:
            raise NotFoundException(f"No existe una pregunta frecuente con id {id}.")
        return pregunta

    async def _validar_no_duplicada(self, texto: str, excluir_id: int | None = None) -> None:
        """La misma pregunta no puede cargarse dos veces (aunque varíe en tildes o signos)."""
        existentes = await self.repo_preguntas.listar(solo_publicadas=False)
        textos = [p.pregunta for p in existentes if p.id != excluir_id]
        if es_pregunta_duplicada(texto, textos):
            raise DuplicateEntryException(
                message="Ya existe una pregunta frecuente con ese mismo texto.",
                errors=[{"field": "pregunta", "message": "La pregunta ya está cargada en la sección."}],
            )

    def _resumir_categorias(self, preguntas: list[PreguntaFrecuenteModel]) -> list[CategoriaPreguntasData]:
        """Categorías en el orden en que aparece su primera pregunta, con su cantidad."""
        conteo: dict[str, int] = {}
        for p in preguntas:
            nombre = categoria_visible(p.categoria)
            conteo[nombre] = conteo.get(nombre, 0) + 1
        return [CategoriaPreguntasData(nombre=nombre, cantidad=cantidad) for nombre, cantidad in conteo.items()]

    def _mapear_publica(self, pregunta: PreguntaFrecuenteModel) -> PreguntaFrecuenteData:
        return PreguntaFrecuenteData(
            id=pregunta.id,
            categoria=categoria_visible(pregunta.categoria),
            pregunta=pregunta.pregunta,
            respuesta=pregunta.respuesta,
            orden=pregunta.orden,
        )

    def _mapear_admin(self, pregunta: PreguntaFrecuenteModel) -> PreguntaFrecuenteAdminData:
        return PreguntaFrecuenteAdminData(
            id=pregunta.id,
            categoria=pregunta.categoria,
            pregunta=pregunta.pregunta,
            respuesta=pregunta.respuesta,
            orden=pregunta.orden,
            publicada=pregunta.publicada,
            created_at=pregunta.created_at,
            updated_at=pregunta.updated_at,
        )
