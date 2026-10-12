from typing import Any, Protocol


class IRepositorioSucursales(Protocol):
    """Protocolo que define el contrato de acceso a datos para Sucursales."""

    async def listar_todas(
        self,
        provincia: str | None = None,
        ciudad: str | None = None,
    ) -> list[Any]:
        """Catálogo de sucursales, opcionalmente filtrado por provincia y/o ciudad (HU09)."""
        ...

    async def obtener_por_id(self, id: int) -> Any | None: ...
