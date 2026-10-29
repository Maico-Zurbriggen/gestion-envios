from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_servicio_empleados,
    requerir_rol,
)
from app.application.interfaces.servicio_empleados import IServicioEmpleados
from app.contracts.empleados import (
    ActualizarEmpleadoRequest,
    CambiarEstadoEmpleadoRequest,
    CrearEmpleadoRequest,
    CrearEmpleadoResponse,
    EmpleadoResponse,
    ListarEmpleadosResponse,
    PasswordRestablecidaResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

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


@router.get(
    "/empleados",
    response_model=ListarEmpleadosResponse,
    summary="Listado de usuarios del personal",
    description="Busca por nombre, DNI, email o teléfono y filtra por rol y estado. Incluye un resumen del personal completo.",
)
async def listar_empleados(
    buscar: str | None = Query(None, max_length=100),
    rol_id: int | None = Query(None, ge=1),
    estado: Literal["Activo", "Inactivo"] | None = Query(None),
    _superadmin=Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    return await servicio_empleados.listar_empleados(buscar=buscar, rol_id=rol_id, estado=estado)


@router.get("/empleados/{id}", response_model=EmpleadoResponse, summary="Detalle de un usuario del personal")
async def obtener_empleado(
    id: UUID,
    _superadmin=Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    return await servicio_empleados.obtener_empleado(id)


@router.patch(
    "/empleados/{id}",
    response_model=EmpleadoResponse,
    summary="Modificar datos o rol de un usuario",
    description="Edición parcial. No permite cambiar el propio rol ni dejar el sistema sin un Superadministrador activo.",
)
async def actualizar_empleado(
    id: UUID,
    datos: ActualizarEmpleadoRequest,
    superadmin: UsuarioModel = Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    return await servicio_empleados.actualizar_empleado(superadmin.id, id, datos)


@router.patch(
    "/empleados/{id}/estado",
    response_model=EmpleadoResponse,
    summary="Dar de baja o reactivar un usuario",
    description="Un usuario Inactivo no puede ingresar ni usar sesiones abiertas. No se borra: conserva su historial.",
)
async def cambiar_estado_empleado(
    id: UUID,
    datos: CambiarEstadoEmpleadoRequest,
    superadmin: UsuarioModel = Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    return await servicio_empleados.cambiar_estado(superadmin.id, id, datos)


@router.post(
    "/empleados/{id}/restablecer-password",
    response_model=PasswordRestablecidaResponse,
    summary="Blanquear la contraseña de un usuario",
    description="Genera una contraseña temporal que se muestra una sola vez; el usuario deberá cambiarla al ingresar.",
)
async def restablecer_password_empleado(
    id: UUID,
    superadmin: UsuarioModel = Depends(requerir_rol(RolEnum.SUPERADMIN)),
    servicio_empleados: IServicioEmpleados = Depends(get_servicio_empleados),
):
    return await servicio_empleados.restablecer_password(superadmin.id, id)
