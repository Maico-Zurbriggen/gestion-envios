from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_servicio_sucursales
from app.application.interfaces.servicio_sucursales import IServicioSucursales
from app.contracts.sucursales import ListarSucursalesResponse

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])


@router.get(
    "",
    response_model=ListarSucursalesResponse,
    status_code=status.HTTP_200_OK,
    summary="Listado público de sucursales disponibles para retiro",
)
async def listar_sucursales(
    servicio_sucursales: IServicioSucursales = Depends(get_servicio_sucursales),
):
    """Endpoint público del catálogo de sucursales, usado por el selector del formulario de registro (HU03)."""
    return await servicio_sucursales.listar_sucursales()
