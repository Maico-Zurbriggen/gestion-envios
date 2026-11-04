from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.dependencies import get_servicio_envios, get_servicio_notificaciones
from app.application.interfaces.servicio_envios import IServicioEnvios
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.contracts.envios import CrearEnvioRequest, CrearEnvioResponse
from app.contracts.notificaciones import DatosNotificacionEnvio

router = APIRouter(prefix="/envios", tags=["Envíos"])


@router.post(
    "",
    response_model=CrearEnvioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro público de un envío con uno o más paquetes",
    description="Registra los datos del emisor, destinatario y paquete(s), genera el token de "
    "seguimiento y el número de cada paquete, y asigna el estado inicial 'Pendiente' (HU03). "
    "Despacha las notificaciones de tracking por email al emisor y destinatario en segundo plano (HU05).",
)
async def crear_envio(
    datos: CrearEnvioRequest,
    background_tasks: BackgroundTasks,
    servicio_envios: IServicioEnvios = Depends(get_servicio_envios),
    servicio_notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    """Endpoint público de registro de envío (HU03) con despacho de notificaciones (HU05)."""
    resultado = await servicio_envios.crear_envio(datos)
    envio_data = resultado.data

    datos_notificacion = DatosNotificacionEnvio(
        envio_id=envio_data.id,
        token_seguimiento=envio_data.token_seguimiento,
        remitente_nombre=envio_data.remitente_nombre,
        remitente_email=envio_data.remitente_email,
        remitente_telefono=envio_data.remitente_telefono,
        destinatario_nombre=envio_data.destinatario_nombre,
        destinatario_email=envio_data.destinatario_email,
        destinatario_telefono=envio_data.destinatario_telefono,
        numeros_paquetes=[p.numero_paquete for p in envio_data.paquetes],
    )
    background_tasks.add_task(servicio_notificaciones.notificar_nuevo_envio, datos_notificacion)

    return resultado
