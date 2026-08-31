from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    get_servicio_empleados,
    requerir_rol,
)
from app.application.interfaces.servicio_empleados import IServicioEmpleados
from app.contracts.empleados import (
    CrearEmpleadoRequest,
    CrearEmpleadoResponse,
)
from app.domain.constants.roles import RolEnum

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.post(
    "/empleados",
    response_model=CrearEmpleadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de empleado administrativo por Superadministrador",
    description="Crea un nuevo empleado en el sistema con estado Activo, flag requiere_cambio_password=True y genera su contraseña temporal.",
)
async def crear_empleado(
    datos: CrearEmpleadoRequest,
    _superadmin=Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    """Endpoint de alta de empleado (HU01)."""
    return await servicio_empleados.crear_empleado(datos)

