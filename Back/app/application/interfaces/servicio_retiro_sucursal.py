from typing import Any, Protocol

from app.contracts.sucursal_retiro import (
    RegistrarRetiroRequest,
    RegistrarRetiroResponse,
    ValidarRetiroResponse,
)


class IServicioRetiroSucursal(Protocol):
    """Protocolo del servicio de gestión de retiro en sucursal (HU13)."""

    async def validar_retiro(self, id_o_codigo: str) -> ValidarRetiroResponse:
        """Verifica la existencia, estado y condiciones previas para retiro en sucursal."""
        ...

    async def registrar_retiro(
        self,
        id_o_codigo: str,
        datos: RegistrarRetiroRequest,
        usuario_admin: Any,
    ) -> RegistrarRetiroResponse:
        """Valida identidades/autorizaciones y registra el retiro físico del paquete."""
        ...
