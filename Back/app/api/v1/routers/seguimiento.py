from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_servicio_seguimiento
from app.application.interfaces.servicio_seguimiento import IServicioSeguimiento
from app.contracts.seguimiento import SeguimientoResponse

router = APIRouter(prefix="/seguimiento", tags=["Seguimiento"])


@router.get(
    "/{token}",
    response_model=SeguimientoResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta pública de seguimiento por token",
    description="Muestra número de paquete, estado, fecha de registro, última actualización, "
    "domicilio y observaciones de todos los paquetes asociados a un token, sin autenticación (HU04).",
)
async def obtener_seguimiento(
    token: str,
    servicio_seguimiento: IServicioSeguimiento = Depends(get_servicio_seguimiento),
):
    """Endpoint público de seguimiento (HU04). Sin autenticación."""
    return await servicio_seguimiento.obtener_seguimiento(token)
