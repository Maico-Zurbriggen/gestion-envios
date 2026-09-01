from typing import Any, Protocol


class IRepositorioSucursales(Protocol):
    """Protocolo que define el contrato de acceso a datos para Sucursales."""

    async def listar_todas(self) -> list[Any]: ...
    async def obtener_por_id(self, id: int) -> Any | None: ...
