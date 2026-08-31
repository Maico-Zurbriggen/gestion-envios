from typing import Any, Optional, Protocol


class IRepositorioRoles(Protocol):
    """Protocolo que define el contrato de acceso a datos para Roles."""

    async def obtener_por_id(self, id: int) -> Optional[Any]: ...
    async def obtener_por_nombre(self, nombre: str) -> Optional[Any]: ...

