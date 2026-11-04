from typing import Any, Protocol


class IRepositorioRoles(Protocol):
    """Protocolo que define el contrato de acceso a datos para Roles."""

    async def obtener_por_id(self, id: int) -> Any | None: ...
    async def obtener_todos(self) -> list[Any]: ...


