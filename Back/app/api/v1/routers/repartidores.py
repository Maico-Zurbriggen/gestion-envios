import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_servicio_repartidores, requerir_roles, sucursales_habilitadas, verificar_sucursal
from app.application.interfaces.servicio_repartidores import IServicioRepartidores
from app.contracts.repartidores import (
    ListarRepartidoresResponse,
    PerfilRepartidorRequest,
    RepartidorResponse,
)
from app.domain.constants.roles import RolEnum

router = APIRouter(prefix="/repartidores", tags=["Logística - Repartidores"])

ROLES_LOGISTICA = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""HU10 es del "personal de logística / administración"."""


@router.get(
    "",
    response_model=ListarRepartidoresResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar repartidores y su perfil operativo (soporte de HU10)",
    description="Lista los usuarios con rol REPARTIDOR. Si se filtra por sucursal, tipo o estado, solo se "
    "devuelven los que ya tienen perfil configurado.",
)
async def listar_repartidores(
    sucursal_id: int | None = Query(None, gt=0),
    tipo_reparto: str | None = Query(None, max_length=10, description="CORTA o LARGA."),
    activo: bool | None = Query(None),
    usuario=Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRepartidores = Depends(get_servicio_repartidores),
):
    verificar_sucursal(usuario, sucursal_id)
    respuesta = await servicio.listar(sucursal_id=sucursal_id, tipo_reparto=tipo_reparto, activo=activo)
    habilitadas = sucursales_habilitadas(usuario)
    if habilitadas is not None:
        # Los de sus sucursales y los que todavía no tienen sucursal base (para poder configurarlos).
        respuesta.data = [r for r in respuesta.data if r.sucursal_base is None or r.sucursal_base.id in habilitadas]
        respuesta.total = len(respuesta.data)
    return respuesta


@router.get(
    "/{usuario_id}",
    response_model=RepartidorResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalle de un repartidor",
)
async def obtener_repartidor(
    usuario_id: uuid.UUID,
    _usuario=Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRepartidores = Depends(get_servicio_repartidores),
):
    return await servicio.obtener(usuario_id)


@router.put(
    "/{usuario_id}/perfil",
    response_model=RepartidorResponse,
    status_code=status.HTTP_200_OK,
    summary="Configurar sucursal base, tipo de reparto y estado de un repartidor",
    description="Crea o reemplaza el perfil operativo. Si el repartidor tiene recorridos activos, no se puede "
    "cambiar su sucursal, su tipo de reparto ni desactivarlo (`409`).",
)
async def configurar_perfil_repartidor(
    usuario_id: uuid.UUID,
    datos: PerfilRepartidorRequest,
    usuario=Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRepartidores = Depends(get_servicio_repartidores),
):
    verificar_sucursal(usuario, datos.sucursal_base_id)
    actual = (await servicio.obtener(usuario_id)).data.sucursal_base
    if actual is not None:
        verificar_sucursal(usuario, actual.id)
    return await servicio.configurar_perfil(usuario_id, datos)
