import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Response

from app.api.dependencies import get_servicio_notificaciones, get_servicio_reparto, requerir_rol
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.application.interfaces.servicio_reparto import IServicioReparto
from app.contracts.recorridos import ListarRecorridosResponse, RecorridoResponse
from app.contracts.reparto import (
    ContactoEntregaResponse,
    EventoEntregaResponse,
    RegistrarEntregaRequest,
    RegistrarVisitaFallidaRequest,
    UbicacionRequest,
    UbicacionResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel


def evitar_cache_privada(respuesta: Response):
    respuesta.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/reparto/recorridos", tags=["Reparto - HU11/HU12"], dependencies=[Depends(evitar_cache_privada)]
)
repartidor_autorizado = requerir_rol(RolEnum.REPARTIDOR)


@router.get("", response_model=ListarRecorridosResponse, summary="Consultar mis recorridos asignados")
async def listar_recorridos(
    fecha: date | None = Query(None),
    estado: str | None = Query(None, max_length=15),
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.listar(usuario, fecha, estado)


@router.get("/{id}", response_model=RecorridoResponse, summary="Recorrido asignado con paradas ordenadas y trazado")
async def obtener_recorrido(
    id: uuid.UUID,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.obtener(id, usuario)


@router.post("/{id}/iniciar", response_model=RecorridoResponse, summary="Iniciar mi recorrido asignado")
async def iniciar_recorrido(
    id: uuid.UUID,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.iniciar(id, usuario)


@router.put(
    "/{id}/ubicacion", response_model=UbicacionResponse, summary="Actualizar la posición en un recorrido activo"
)
async def actualizar_ubicacion(
    id: uuid.UUID,
    datos: UbicacionRequest,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.actualizar_ubicacion(id, datos, usuario)


@router.get("/{id}/ubicacion", response_model=UbicacionResponse, summary="Consultar la última posición de mi recorrido")
async def obtener_ubicacion(
    id: uuid.UUID,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.obtener_ubicacion(id, usuario)


@router.get(
    "/{id}/paquetes/{codigo}/contacto",
    response_model=ContactoEntregaResponse,
    summary="Teléfono del destinatario del paquete a entregar",
)
async def obtener_contacto(
    id: uuid.UUID,
    codigo: str = Path(..., max_length=40),
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.contacto(id, codigo, usuario)


@router.post(
    "/{id}/paquetes/{codigo}/entrega",
    response_model=EventoEntregaResponse,
    summary="Registrar entrega con receptor, firma y fecha/hora del servidor",
)
async def registrar_entrega(
    id: uuid.UUID,
    datos: RegistrarEntregaRequest,
    codigo: str = Path(..., max_length=40),
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    return await servicio.registrar_entrega(id, codigo, datos, usuario)


@router.post(
    "/{id}/paquetes/{codigo}/visita-fallida",
    response_model=EventoEntregaResponse,
    summary="Registrar visita fallida y generar aviso por email",
)
async def registrar_visita_fallida(
    id: uuid.UUID,
    datos: RegistrarVisitaFallidaRequest,
    tareas: BackgroundTasks,
    codigo: str = Path(..., max_length=40),
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    resultado = await servicio.registrar_visita_fallida(id, codigo, datos, usuario)
    tareas.add_task(notificaciones.notificar_visita_fallida, resultado.data.evento_id)
    return resultado


@router.get(
    "/{id}/entregas/{evento_id}/firma",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    summary="Consultar constancia de firma autorizada",
)
async def obtener_firma(
    id: uuid.UUID,
    evento_id: uuid.UUID,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    firma = await servicio.obtener_firma(id, evento_id, usuario)
    return Response(
        content=firma,
        media_type="image/png",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
