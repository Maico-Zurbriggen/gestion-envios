from typing import Protocol

from app.contracts.envios import CrearEnvioRequest, CrearEnvioResponse


class IServicioEnvios(Protocol):
    """Protocolo del servicio de registro público de envíos (HU03)."""

    async def crear_envio(self, datos: CrearEnvioRequest) -> CrearEnvioResponse: ...
