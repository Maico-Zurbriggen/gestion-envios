from typing import Protocol
from uuid import UUID

from app.contracts.repartidores import (
    ListarRepartidoresResponse,
    PerfilRepartidorRequest,
    RepartidorResponse,
)


class IServicioRepartidores(Protocol):
    """Protocolo del servicio de perfiles de repartidor (soporte de HU10)."""

    async def listar(
        self,
        sucursal_id: int | None = None,
        tipo_reparto: str | None = None,
        activo: bool | None = None,
    ) -> ListarRepartidoresResponse: ...

    async def obtener(self, usuario_id: UUID) -> RepartidorResponse: ...

    async def configurar_perfil(self, usuario_id: UUID, datos: PerfilRepartidorRequest) -> RepartidorResponse:
        """Crea o actualiza la sucursal base, el tipo de reparto y el estado operativo."""
        ...
