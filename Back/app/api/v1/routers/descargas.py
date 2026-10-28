"""Control de descarga en la sucursal de destino (escaneo de lo que baja del vehículo)."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_servicio_descargas, requerir_roles
from app.application.services.servicio_descargas import ServicioDescargas
from app.contracts.descargas import (
    CerrarControlRequest,
    ControlDescargaResponse,
    IniciarControlRequest,
    RecorridosEntrantesResponse,
    RegistrarLecturaRequest,
    ResultadoLecturaResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/terminal/descargas", tags=["Control de descarga"])
PERSONAL = [RolEnum.VENDEDOR, RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""El mismo personal que recibe paquetes en la terminal."""


@router.get(
    "/recorridos",
    response_model=RecorridosEntrantesResponse,
    summary="Recorridos de larga distancia que dejan paquetes en la sucursal",
)
async def recorridos_entrantes(
    sucursal_id: int = Query(..., ge=1),
    _usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    return await servicio.recorridos_entrantes(sucursal_id)


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
    return await servicio.iniciar(datos, usuario)


@router.get("/{id}", response_model=ControlDescargaResponse, summary="Estado del control: esperados, verificados y sobrantes")
async def detalle_control(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    return await servicio.detalle(id)


@router.post("/{id}/lecturas", response_model=ResultadoLecturaResponse, summary="Registrar un paquete escaneado")
async def registrar_lectura(
    id: uuid.UUID,
    datos: RegistrarLecturaRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    return await servicio.registrar_lectura(id, datos, usuario)


@router.post("/{id}/cerrar", response_model=ControlDescargaResponse, summary="Cerrar el control y registrar los faltantes")
async def cerrar_control(
    id: uuid.UUID,
    datos: CerrarControlRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioDescargas = Depends(get_servicio_descargas),
):
    return await servicio.cerrar(id, datos, usuario)
