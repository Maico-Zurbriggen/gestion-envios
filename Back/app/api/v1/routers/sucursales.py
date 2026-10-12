from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_servicio_sucursales
from app.application.interfaces.servicio_sucursales import IServicioSucursales
from app.contracts.sucursales import ListarSucursalesResponse, OpcionesRetiroResponse

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])


@router.get(
    "",
    response_model=ListarSucursalesResponse,
    status_code=status.HTTP_200_OK,
    summary="Listado público de sucursales disponibles para retiro",
    description="Catálogo público de sucursales, opcionalmente filtrado por provincia y/o ciudad. "
    "Alimenta el selector de retiro en sucursal del formulario de registro (HU03) y la vista pública "
    "de sucursales disponibles para retiro (HU09).",
)
async def listar_sucursales(
    provincia: str | None = Query(
        None,
        description="Filtra por provincia (comparación sin distinguir mayúsculas).",
        max_length=100,
    ),
    ciudad: str | None = Query(
        None,
        description="Filtra por ciudad (comparación sin distinguir mayúsculas).",
        max_length=100,
    ),
    servicio_sucursales: IServicioSucursales = Depends(get_servicio_sucursales),
):
    """Endpoint público del catálogo de sucursales, usado por el selector de HU03 y por la vista de HU09."""
    return await servicio_sucursales.listar_sucursales(provincia=provincia, ciudad=ciudad)


@router.get(
    "/opciones-retiro/{token}",
    response_model=OpcionesRetiroResponse,
    status_code=status.HTTP_200_OK,
    summary="Sucursales disponibles para retirar un envío (HU09)",
    description="Dado el token de seguimiento de un envío, devuelve la sucursal asignada para el retiro, "
    "las otras sucursales de esa misma ciudad, el estado de cada paquete y los requisitos para retirar. "
    "Si el envío es a domicilio responde 200 con `aplica_retiro = false` y el motivo. Público, sin autenticación.",
)
async def obtener_opciones_retiro(
    token: str = Path(..., description="Token de seguimiento del envío (`ENV-XXXXXXXXXX`)."),
    servicio_sucursales: IServicioSucursales = Depends(get_servicio_sucursales),
):
    """Endpoint público de opciones de retiro en sucursal (HU09). Sin autenticación."""
    return await servicio_sucursales.obtener_opciones_retiro(token)
