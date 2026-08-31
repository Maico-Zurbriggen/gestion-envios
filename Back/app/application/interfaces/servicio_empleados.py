from typing import Protocol

from app.contracts.empleados import CrearEmpleadoRequest, CrearEmpleadoResponse


class IServicioEmpleados(Protocol):
    """Protocolo del servicio de administración y alta de empleados."""

    async def crear_empleado(
        self, datos: CrearEmpleadoRequest
    ) -> CrearEmpleadoResponse: ...

