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

    async def obtener_por_nombre(self, nombre: str) -> Any | None: ...

    async def obtener_varias(self, ids: list[int]) -> list[Any]: ...

    async def contar_usuarios(self) -> dict[int, int]: ...

    def nueva(self, **datos: Any) -> Any:
        """Sucursal sin guardar todavía."""
        ...

    async def guardar(self, sucursal: Any) -> Any: ...
