from typing import Any, Protocol


class IRepositorioPreguntasFrecuentes(Protocol):
    """Protocolo de acceso a datos de la sección de preguntas frecuentes (HU08)."""

    async def listar(self, solo_publicadas: bool = True) -> list[Any]:
        """Preguntas ordenadas por `orden` y luego por `id`. Con
        `solo_publicadas=False` incluye las ocultas (vista de administración)."""
        ...

    async def obtener_por_id(self, id: int) -> Any | None: ...

    async def crear(self, pregunta: Any) -> Any: ...

    async def actualizar(self, pregunta: Any) -> Any:
        """Persiste los cambios ya aplicados sobre la entidad."""
        ...

    async def eliminar(self, pregunta: Any) -> None: ...
