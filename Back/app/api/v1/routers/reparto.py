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
    OptimizarRecorridoRequest,
    RegistrarEntregaRequest,
    RegistrarLlegadaRequest,
    RegistrarVisitaFallidaRequest,
    UbicacionRequest,
    UbicacionResponse,
)
from app.domain.constants.estados_logistica import TipoAvisoEnum, TipoDistanciaEnum
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
    tareas: BackgroundTasks,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    resultado = await servicio.iniciar(id, usuario)
    # Corta distancia: cada destinatario recibe el aviso de que su paquete llega hoy.
    if resultado.data.tipo_distancia == TipoDistanciaEnum.CORTA.value:
        for parada in resultado.data.paradas:
            for paquete in parada.paquetes:
                tareas.add_task(notificaciones.notificar_hito, paquete.paquete_id, TipoAvisoEnum.EN_REPARTO.value)
    return resultado


@router.post(
    "/{id}/optimizar",
    response_model=RecorridoResponse,
    summary="Optimizar mi recorrido",
    description="Recalcula el orden más rápido por calles de las paradas pendientes, desde la ubicación enviada.",
)
async def optimizar_recorrido(
    id: uuid.UUID,
    datos: OptimizarRecorridoRequest | None = None,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
):
    desde = (datos.latitud, datos.longitud) if datos and datos.latitud is not None and datos.longitud is not None else None
    return await servicio.optimizar(id, usuario, desde)


@router.post(
    "/{id}/llegadas",
    response_model=RecorridoResponse,
    summary="Marcar la llegada a la próxima sucursal del recorrido (respaldo)",
    description="Recorridos entre sucursales. La llegada se registra sola por proximidad (10 km) al enviar la "
    "ubicación; si el GPS no la registró, el repartidor la marca desde el celular. Los paquetes que bajan ahí se "
    "actualizan y, si quedan listos para retirar, se avisa al cliente por email y WhatsApp.",
)
async def registrar_llegada(
    id: uuid.UUID,
    datos: RegistrarLlegadaRequest,
    tareas: BackgroundTasks,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    respuesta, listos = await servicio.registrar_llegada(id, datos, usuario)
    for paquete_id in listos:
        tareas.add_task(notificaciones.notificar_hito, paquete_id, TipoAvisoEnum.LISTO_PARA_RETIRO.value)
    return respuesta


@router.put(
    "/{id}/ubicacion",
    response_model=UbicacionResponse,
    summary="Actualizar la posición en un recorrido activo",
    description="En larga distancia, a 10 km o menos de la próxima sucursal registra la llegada (HU11 CA3).",
)
async def actualizar_ubicacion(
    id: uuid.UUID,
    datos: UbicacionRequest,
    tareas: BackgroundTasks,
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    respuesta, listos = await servicio.actualizar_ubicacion(id, datos, usuario)
    for paquete_id in listos:
        tareas.add_task(notificaciones.notificar_hito, paquete_id, TipoAvisoEnum.LISTO_PARA_RETIRO.value)
    return respuesta


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
    tareas: BackgroundTasks,
    codigo: str = Path(..., max_length=40),
    usuario: UsuarioModel = Depends(repartidor_autorizado),
    servicio: IServicioReparto = Depends(get_servicio_reparto),
    notificaciones: IServicioNotificaciones = Depends(get_servicio_notificaciones),
):
    resultado = await servicio.registrar_entrega(id, codigo, datos, usuario)
    tareas.add_task(notificaciones.notificar_hito, resultado.data.paquete_id, TipoAvisoEnum.ENTREGADO.value)
    return resultado


@router.post(
    "/{id}/paquetes/{codigo}/visita-fallida",
    response_model=EventoEntregaResponse,
    summary="Registrar visita fallida y generar aviso por email y WhatsApp",
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
