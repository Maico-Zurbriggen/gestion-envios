from typing import Any, Protocol

from app.contracts.recepcion_terminal import (
    EscanearPaqueteResponse,
    RecepcionarPaqueteRequest,
    RecepcionarPaqueteResponse,
)


class IServicioRecepcionTerminal(Protocol):
    """Protocolo del servicio de recepción de paquetes en la terminal (HU06)."""

    async def escanear_paquete(self, codigo: str) -> EscanearPaqueteResponse:
        """Identifica el paquete precargado a partir del código de barras de la planilla."""
        ...

    async def recepcionar_paquete(
        self,
        codigo: str,
        datos: RecepcionarPaqueteRequest,
        usuario_vendedor: Any,
    ) -> RecepcionarPaqueteResponse:
        """Deja el paquete registrado en la terminal como listo para su envío."""
        ...
