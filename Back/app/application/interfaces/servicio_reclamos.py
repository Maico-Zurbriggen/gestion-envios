from typing import Any, Protocol
from uuid import UUID

from app.contracts.reclamos import (
    ActualizarEstadoReclamoRequest,
    CrearReclamoRequest,
    CrearReclamoResponse,
    InicioReclamoResponse,
    ListarReclamosAdminResponse,
    ReclamoAdminResponse,
)


class IServicioReclamos(Protocol):
    """Protocolo del servicio de reclamos iniciados desde la vista pública (HU07)."""

    async def obtener_inicio_reclamo(self, token: str) -> InicioReclamoResponse:
        """Habilita el inicio de un reclamo para el envío del token (HU07 Escenario 1)."""
        ...

    async def crear_reclamo(self, token: str, datos: CrearReclamoRequest) -> CrearReclamoResponse:
        """Registra un reclamo para el envío consultado con el token."""
        ...

    async def listar_reclamos(
        self,
        estado: str | None = None,
        tipo: str | None = None,
        token_seguimiento: str | None = None,
    ) -> ListarReclamosAdminResponse:
        """Bandeja interna de reclamos."""
        ...

    async def obtener_reclamo(self, id: UUID) -> ReclamoAdminResponse: ...

    async def actualizar_estado(
        self,
        id: UUID,
        datos: ActualizarEstadoReclamoRequest,
        usuario_gestion: Any,
    ) -> ReclamoAdminResponse:
        """Avanza el reclamo en su máquina de estados."""
        ...
