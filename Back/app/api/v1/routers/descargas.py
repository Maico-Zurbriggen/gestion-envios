"""Control de carga (sucursal de origen) y de descarga (sucursal de destino) de los recorridos."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.dependencies import get_servicio_descargas, get_servicio_notificaciones, requerir_roles, verificar_sucursal
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.application.services.servicio_descargas import ServicioDescargas
from app.contracts.descargas import (
    CerrarControlRequest,
    ControlDescargaResponse,
    IniciarControlRequest,
    RecorridosEntrantesResponse,
    RegistrarLecturaRequest,
    ResultadoLecturaResponse,
)
from app.domain.constants.estados_logistica import TipoAvisoEnum
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/terminal/descargas", tags=["Control de carga y descarga"])
PERSONAL = [RolEnum.VENDEDOR, RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""El mismo personal que recibe paquetes en la terminal."""


@router.get(
    "/recorridos",
    response_model=RecorridosEntrantesResponse,
    summary="Recorridos de larga distancia que dejan paquetes en la sucursal",
)
async def recorridos_entrantes(
    sucursal_id: int = Query(..., ge=1),
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    verificar_sucursal(usuario, sucursal_id)
    return await servicio.recorridos_entrantes(sucursal_id)


@router.get(
    "/recorridos-salientes",
    response_model=RecorridosEntrantesResponse,
    summary="Recorridos que salen de la sucursal y todavía no iniciaron (control de carga)",
)
async def recorridos_salientes(
    sucursal_id: int = Query(..., ge=1),
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    verificar_sucursal(usuario, sucursal_id)
    return await servicio.recorridos_salientes(sucursal_id)


@router.post(
    "",
    response_model=ControlDescargaResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar (o retomar) el control de descarga de un recorrido en una sucursal",
)
async def iniciar_control(
    datos: IniciarControlRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    verificar_sucursal(usuario, datos.sucursal_id)
    return await servicio.iniciar(datos, usuario)


@router.get("/{id}", response_model=ControlDescargaResponse, summary="Estado del control: esperados, verificados y sobrantes")
async def detalle_control(
    id: uuid.UUID,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    return await _de_mi_sucursal(id, usuario, servicio)


@router.post("/{id}/lecturas", response_model=ResultadoLecturaResponse, summary="Registrar un paquete escaneado")
async def registrar_lectura(
    id: uuid.UUID,
    datos: RegistrarLecturaRequest,
    tareas: BackgroundTasks,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    await _de_mi_sucursal(id, usuario, servicio)
    resultado = await servicio.registrar_lectura(id, datos, usuario)
    if resultado.data.listo_para_retiro and resultado.data.paquete_id and not resultado.data.repetida:
        tareas.add_task(notificaciones.notificar_hito, resultado.data.paquete_id, TipoAvisoEnum.LISTO_PARA_RETIRO.value)
    return resultado


@router.post("/{id}/cerrar", response_model=ControlDescargaResponse, summary="Cerrar el control y registrar los faltantes")
async def cerrar_control(
    id: uuid.UUID,
    datos: CerrarControlRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    await _de_mi_sucursal(id, usuario, servicio)
    return await servicio.cerrar(id, datos, usuario)


async def _de_mi_sucursal(id: uuid.UUID, usuario: UsuarioModel, servicio: ServicioDescargas):
    """El control tiene que ser de una sucursal habilitada para el usuario."""
    control = await servicio.detalle(id)
    verificar_sucursal(usuario, control.data.sucursal.id)
    return control
