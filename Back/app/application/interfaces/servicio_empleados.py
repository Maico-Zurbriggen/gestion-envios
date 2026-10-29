from typing import Protocol
from uuid import UUID

from app.contracts.empleados import (
    ActualizarEmpleadoRequest,
    CambiarEstadoEmpleadoRequest,
    CrearEmpleadoRequest,
    CrearEmpleadoResponse,
    EmpleadoResponse,
    ListarEmpleadosResponse,
    PasswordRestablecidaResponse,
)


class IServicioEmpleados(Protocol):
    """Protocolo del servicio de administración de usuarios del personal."""

    async def crear_empleado(
        self, datos: CrearEmpleadoRequest
    ) -> CrearEmpleadoResponse: ...

    async def listar_empleados(
        self, buscar: str | None = None, rol_id: int | None = None, estado: str | None = None
    ) -> ListarEmpleadosResponse: ...

    async def obtener_empleado(self, id: UUID) -> EmpleadoResponse: ...

    async def actualizar_empleado(
        self, actor_id: UUID, id: UUID, datos: ActualizarEmpleadoRequest
    ) -> EmpleadoResponse: ...

    async def cambiar_estado(
        self, actor_id: UUID, id: UUID, datos: CambiarEstadoEmpleadoRequest
    ) -> EmpleadoResponse: ...

    async def restablecer_password(self, actor_id: UUID, id: UUID) -> PasswordRestablecidaResponse: ...
