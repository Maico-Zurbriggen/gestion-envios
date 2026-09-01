from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_servicio_envios
from app.application.interfaces.servicio_envios import IServicioEnvios
from app.contracts.envios import CrearEnvioRequest, CrearEnvioResponse

router = APIRouter(prefix="/envios", tags=["Envíos"])


@router.post(
    "",
    response_model=CrearEnvioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro público de un envío con uno o más paquetes",
    description="Registra los datos del emisor, destinatario y paquete(s), genera el token de "
    "seguimiento y el número de cada paquete, y asigna el estado inicial 'Pendiente' (HU03).",
)
async def crear_envio(
    datos: CrearEnvioRequest,
    servicio_envios: IServicioEnvios = Depends(get_servicio_envios),
):
    """Endpoint público de registro de envío (HU03). Sin autenticación."""
    return await servicio_envios.crear_envio(datos)
