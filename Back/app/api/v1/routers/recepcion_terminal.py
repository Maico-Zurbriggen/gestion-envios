from fastapi import APIRouter, Depends, Path, status

from app.api.dependencies import get_servicio_recepcion_terminal, requerir_roles
from app.application.interfaces.servicio_recepcion_terminal import IServicioRecepcionTerminal
from app.contracts.recepcion_terminal import (
    EscanearPaqueteResponse,
    RecepcionarPaqueteRequest,
    RecepcionarPaqueteResponse,
)
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
    codigo: str = Path(
        ...,
        description="Valor leído del código de barras de la planilla (`PAQ-XXXXXXXXXX`) o UUID del paquete.",
    ),
    usuario_vendedor: UsuarioModel = Depends(requerir_roles(ROLES_TERMINAL)),
    servicio_recepcion: IServicioRecepcionTerminal = Depends(get_servicio_recepcion_terminal),
):
    """Endpoint de recepción del paquete en terminal. Requiere rol VENDEDOR, ADMINISTRATIVO o SUPERADMIN."""
    return await servicio_recepcion.recepcionar_paquete(
        codigo=codigo,
        datos=datos,
        usuario_vendedor=usuario_vendedor,
    )
