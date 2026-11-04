from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

from app.api.dependencies import (
    get_servicio_notificaciones,
    get_servicio_recepcion_terminal,
    requerir_roles,
    verificar_sucursal,
)
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.application.interfaces.servicio_recepcion_terminal import IServicioRecepcionTerminal
from app.contracts.recepcion_terminal import (
    EscanearPaqueteResponse,
    RecepcionarPaqueteRequest,
    RecepcionarPaqueteResponse,
)
from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoAvisoEnum
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/terminal/paquetes", tags=["Terminal - Recepción de Paquetes"])

ROLES_TERMINAL = [RolEnum.VENDEDOR, RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""HU06 es del vendedor/personal de terminal; se habilita también a
ADMINISTRATIVO y SUPERADMIN porque en sucursales chicas la misma persona
atiende el mostrador y administra, y bloquearlos obligaría a crear un
segundo usuario para la misma tarea."""


@router.get(
    "/{codigo}/escanear",
    response_model=EscanearPaqueteResponse,
    status_code=status.HTTP_200_OK,
    summary="Identificar un paquete precargado por su código de barras (HU06)",
    description="Identifica el paquete a partir del código de barras impreso en la planilla del envío "
    "(`PAQ-XXXXXXXXXX`) o de su identificador interno, y devuelve los datos del paquete y del envío para "
    "que el vendedor los contraste con lo que tiene en el mostrador. No modifica el paquete.",
)
async def escanear_paquete(
    codigo: str = Path(
        ...,
        description="Valor leído del código de barras de la planilla (`PAQ-XXXXXXXXXX`) o UUID del paquete.",
    ),
    usuario_vendedor: UsuarioModel = Depends(requerir_roles(ROLES_TERMINAL)),
    servicio_recepcion: IServicioRecepcionTerminal = Depends(get_servicio_recepcion_terminal),
):
    """Endpoint de identificación del paquete escaneado. Requiere rol VENDEDOR, ADMINISTRATIVO o SUPERADMIN."""
    return await servicio_recepcion.escanear_paquete(codigo)


@router.post(
    "/{codigo}/recepcionar",
    response_model=RecepcionarPaqueteResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar la recepción del paquete en la terminal (HU06)",
    description="Deja el paquete registrado en la terminal como listo para su respectivo envío: pasa su "
    "estado a `EN_SUCURSAL_ORIGEN`, fija la sucursal donde quedó ubicado y agrega la entrada "
    "correspondiente al historial de estados del paquete.",
)
async def recepcionar_paquete(
    datos: RecepcionarPaqueteRequest,
    tareas: BackgroundTasks,
    codigo: str = Path(
        ...,
        description="Valor leído del código de barras de la planilla (`PAQ-XXXXXXXXXX`) o UUID del paquete.",
    ),
    usuario_vendedor: UsuarioModel = Depends(requerir_roles(ROLES_TERMINAL)),
    servicio_recepcion: IServicioRecepcionTerminal = Depends(get_servicio_recepcion_terminal),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    verificar_sucursal(usuario_vendedor, datos.sucursal_id)
    """Endpoint de recepción del paquete en terminal. Requiere rol VENDEDOR, ADMINISTRATIVO o SUPERADMIN."""
    resultado = await servicio_recepcion.recepcionar_paquete(
        codigo=codigo,
        datos=datos,
        usuario_vendedor=usuario_vendedor,
    )
    # El remitente sabe que su paquete entró a la red; si ya está en la sucursal de
    # retiro, el destinatario sabe que puede pasar a buscarlo.
    tareas.add_task(notificaciones.notificar_hito, resultado.data.paquete_id, TipoAvisoEnum.ADMITIDO.value)
    if resultado.data.estado == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value:
        tareas.add_task(notificaciones.notificar_hito, resultado.data.paquete_id, TipoAvisoEnum.LISTO_PARA_RETIRO.value)
    return resultado
