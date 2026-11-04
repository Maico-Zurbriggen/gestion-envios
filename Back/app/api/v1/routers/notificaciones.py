from fastapi import APIRouter, Depends, Path, status

from app.api.dependencies import get_servicio_notificaciones, requerir_roles
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.contracts.notificaciones import NotificacionesEnvioResponse
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/envios/{token}/notificaciones", tags=["Notificaciones (HU05)"])

ROLES_NOTIFICACIONES = [RolEnum.VENDEDOR, RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""El personal de terminal y de sucursal es quien atiende al cliente que dice no haber recibido el token."""

TOKEN_PATH = Path(..., description="Código de seguimiento del envío (`ENV-XXXXXXXXXX`).")


@router.get(
    "",
    response_model=NotificacionesEnvioResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar el resultado de las notificaciones de un envío (HU05)",
    description="Devuelve cada intento por canal (email y WhatsApp) y destinatario (remitente y destinatario), "
    "con su estado y el motivo del fallo si lo hubo.",
)
async def listar_notificaciones(
    token: str = TOKEN_PATH,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_NOTIFICACIONES)),
    servicio: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    return await servicio.listar_por_token(token)


@router.post(
    "/reintentar",
    response_model=NotificacionesEnvioResponse,
    status_code=status.HTTP_200_OK,
    summary="Reintentar las notificaciones pendientes o fallidas de un envío (HU05)",
    description="Vuelve a despachar solo los intentos que no se enviaron. Los ya enviados nunca se repiten.",
)
async def reintentar_notificaciones(
    token: str = TOKEN_PATH,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_NOTIFICACIONES)),
    servicio: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    return await servicio.reintentar_por_token(token)
