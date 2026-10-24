import uuid

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_servicio_reclamos, requerir_roles
from app.application.interfaces.servicio_reclamos import IServicioReclamos
from app.contracts.reclamos import (
    ActualizarEstadoReclamoRequest,
    CrearReclamoRequest,
    CrearReclamoResponse,
    InicioReclamoResponse,
    ListarReclamosAdminResponse,
    ReclamoAdminResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/reclamos", tags=["Reclamos"])
router_admin = APIRouter(prefix="/admin/reclamos", tags=["Administración - Reclamos"])

ROLES_GESTION_RECLAMOS = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""Quienes atienden los reclamos. El reclamo se inicia sin sesión; su gestión
es una tarea administrativa, no de mostrador ni de reparto."""

TOKEN_PATH = Path(..., description="Token de seguimiento del envío (`ENV-XXXXXXXXXX`).", max_length=40)


# --- Vista pública del token (HU07) ---


@router.get(
    "/seguimiento/{token}",
    response_model=InicioReclamoResponse,
    status_code=status.HTTP_200_OK,
    summary="Habilitar el inicio de un reclamo desde la vista pública del token (HU07)",
    description="Dado el token de seguimiento, devuelve si se puede iniciar un reclamo, los tipos de reclamo, "
    "los paquetes del envío y los reclamos ya iniciados con su estado. Público, sin autenticación.",
)
async def obtener_inicio_reclamo(
    token: str = TOKEN_PATH,
    servicio: IServicioReclamos = Depends(get_servicio_reclamos),
):
    """Endpoint público (HU07 Escenario 1). Sin autenticación."""
    return await servicio.obtener_inicio_reclamo(token)


@router.post(
    "/seguimiento/{token}",
    response_model=CrearReclamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar un reclamo para el envío consultado (HU07)",
    description="Registra un reclamo en estado `ABIERTO` para el envío del token. Exige al menos un medio de "
    "contacto, rechaza un paquete que no sea del envío y un reclamo duplicado (mismo tipo y mismo paquete "
    "con otro reclamo en curso). Público, sin autenticación.",
)
async def crear_reclamo(
    datos: CrearReclamoRequest,
    token: str = TOKEN_PATH,
    servicio: IServicioReclamos = Depends(get_servicio_reclamos),
):
    """Endpoint público de alta de reclamo (HU07). Sin autenticación."""
    return await servicio.crear_reclamo(token, datos)


# --- Gestión interna ---


@router_admin.get(
    "",
    response_model=ListarReclamosAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Bandeja de reclamos",
    description="Lista los reclamos, del más reciente al más antiguo, con los datos de contacto de quien reclamó.",
)
async def listar_reclamos(
    estado: str | None = Query(None, max_length=15, description="ABIERTO, EN_REVISION, RESUELTO o RECHAZADO."),
    tipo: str | None = Query(None, max_length=20, description="DEMORA, DANIO, EXTRAVIO u OTRO."),
    token: str | None = Query(None, max_length=40, description="Token de seguimiento del envío."),
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_GESTION_RECLAMOS)),
    servicio: IServicioReclamos = Depends(get_servicio_reclamos),
):
    return await servicio.listar_reclamos(estado=estado, tipo=tipo, token_seguimiento=token)


@router_admin.get(
    "/{id}",
    response_model=ReclamoAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalle de un reclamo",
)
async def obtener_reclamo(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_GESTION_RECLAMOS)),
    servicio: IServicioReclamos = Depends(get_servicio_reclamos),
):
    return await servicio.obtener_reclamo(id)


@router_admin.patch(
    "/{id}/estado",
    response_model=ReclamoAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambiar el estado de un reclamo",
    description="Transiciones válidas: ABIERTO → EN_REVISION | RESUELTO | RECHAZADO; EN_REVISION → RESUELTO | "
    "RECHAZADO. Cerrar el reclamo exige `resolucion`, que es lo que se muestra en la vista pública.",
)
async def actualizar_estado_reclamo(
    id: uuid.UUID,
    datos: ActualizarEstadoReclamoRequest,
    usuario: UsuarioModel = Depends(requerir_roles(ROLES_GESTION_RECLAMOS)),
    servicio: IServicioReclamos = Depends(get_servicio_reclamos),
):
    return await servicio.actualizar_estado(id, datos, usuario_gestion=usuario)
