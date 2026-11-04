from typing import Any, Protocol
from uuid import UUID


class IRepositorioRepartidores(Protocol):
    """Protocolo de acceso a datos de los repartidores y sus perfiles (soporte de HU10)."""

    async def listar(
        self,
        sucursal_id: int | None = None,
        tipo_reparto: str | None = None,
        activo: bool | None = None,
    ) -> list[Any]:
        """Usuarios con rol REPARTIDOR con su perfil precargado. Si se filtra por
        algún dato del perfil, solo devuelve los que tienen perfil."""
        ...

    async def obtener_usuario(self, usuario_id: UUID) -> Any | None:
        """Usuario (de cualquier rol) con su perfil de repartidor precargado."""
        ...

    async def guardar_perfil(self, perfil: Any) -> Any:
        """Inserta o actualiza el perfil y lo devuelve con su sucursal base cargada."""
        ...

    async def tiene_recorridos_activos(self, usuario_id: UUID) -> bool:
        """Indica si el repartidor tiene recorridos generados, en edición o en curso."""
        ...
