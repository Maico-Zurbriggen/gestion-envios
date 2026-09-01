from typing import Protocol

from app.contracts.seguimiento import SeguimientoResponse


class IServicioSeguimiento(Protocol):
    """Protocolo del servicio de consulta pública de seguimiento (HU04)."""

    async def obtener_seguimiento(self, token: str) -> SeguimientoResponse: ...
