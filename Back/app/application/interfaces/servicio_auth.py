from typing import Protocol, Union
from uuid import UUID

from app.contracts.auth import (
    CambiarPasswordResponse,
    LoginRequiresPasswordChangeResponse,
    LoginSuccessResponse,
)


class IServicioAuth(Protocol):
    """Protocolo del servicio de autenticación y gestión de sesiones."""

    async def autenticar_usuario(
        self, dni: str, password_plana: str
    ) -> Union[LoginSuccessResponse, LoginRequiresPasswordChangeResponse]: ...

    async def cambiar_password(
        self,
        usuario_id: UUID,
        password_actual: str,
        nueva_password: str,
        confirmacion_password: str,
    ) -> CambiarPasswordResponse: ...

