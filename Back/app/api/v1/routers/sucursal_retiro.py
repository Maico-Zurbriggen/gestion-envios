from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_servicio_retiro_sucursal, requerir_roles
from app.application.interfaces.servicio_retiro_sucursal import IServicioRetiroSucursal
from app.contracts.sucursal_retiro import (
    RegistrarRetiroRequest,
    RegistrarRetiroResponse,
    ValidarRetiroResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/sucursal/paquetes", tags=["Sucursal - Retiro de Paquetes"])


@router.get(
    "/{id_o_codigo}/validar-retiro",
    response_model=ValidarRetiroResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar condiciones para retiro de paquete en sucursal (HU13)",
    description="Permite al personal administrativo de sucursal consultar un paquete por su ID (UUID) o "
    "código alfanumérico (PAQ-XXXXXXXXXX) para validar si se encuentra listo para retiro e inspeccionar "
    "los datos del destinatario para contrastar identidad física.",
)
async def validar_retiro(
    id_o_codigo: str,
    usuario_admin: UsuarioModel = Depends(requerir_roles([RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN])),
    servicio_retiro: IServicioRetiroSucursal = Depends(get_servicio_retiro_sucursal),
):
    """Endpoint de validación de disponibilidad de retiro en sucursal. Requiere rol ADMINISTRATIVO."""
    return await servicio_retiro.validar_retiro(id_o_codigo)


@router.post(
    "/{id}/registrar-retiro",
    response_model=RegistrarRetiroResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar retiro físico de paquete en sucursal (HU13)",
    description="Registra la entrega física presencial del paquete en sucursal. Valida identidad del titular "
    "(mayor o igual a 16 años con documento) o acreditación de tercero autorizado (documento propio, copia "
    "DNI titular y constancia de autorización firmada). Actualiza el estado a ENTREGADO_EN_SUCURSAL.",
)
async def registrar_retiro(
    id: str,
    datos: RegistrarRetiroRequest,
    usuario_admin: UsuarioModel = Depends(requerir_roles([RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN])),
    servicio_retiro: IServicioRetiroSucursal = Depends(get_servicio_retiro_sucursal),
):
    """Endpoint para registrar el retiro presencial de un paquete en sucursal. Requiere rol ADMINISTRATIVO."""
    return await servicio_retiro.registrar_retiro(
        id_o_codigo=id,
        datos=datos,
        usuario_admin=usuario_admin,
    )
