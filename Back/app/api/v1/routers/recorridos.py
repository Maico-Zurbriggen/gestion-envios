import uuid
from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_servicio_recorridos, requerir_roles
from app.application.interfaces.servicio_recorridos import IServicioRecorridos
from app.contracts.recorridos import (
    AlertaRecorridoResponse,
    CompletarUbicacionPaqueteRequest,
    EliminarRecorridoResponse,
    GenerarRecorridosRequest,
    GenerarRecorridosResponse,
    ListarAlertasRecorridoResponse,
    ListarRecorridosResponse,
    ReasignarRepartidorRequest,
    RecorridoResponse,
    ReemplazarPaquetesRecorridoRequest,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/recorridos", tags=["Logística - Recorridos"])

ROLES_LOGISTICA = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""HU10 es del "personal de logística / administración". El repartidor ve su
recorrido desde la aplicación móvil de HU11, no desde estos endpoints."""


# --- Escenario 1: generación automática ---


@router.post(
    "/generar",
    response_model=GenerarRecorridosResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar automáticamente los recorridos de una sucursal (HU10)",
    description="Toma los paquetes listos en la sucursal que necesitan un recorrido del tipo pedido (CORTA: "
    "entregas a domicilio en la ciudad; LARGA: traslados a otras sucursales), los reparte de forma equitativa "
    "entre los repartidores disponibles por zonas alrededor de la sucursal y ordena cada recorrido para "
    "minimizar el tiempo, considerando la orientación de las calles. Devuelve los recorridos y las alertas de "
    "los paquetes que quedaron sin recorrido.",
)
async def generar_recorridos(
    datos: GenerarRecorridosRequest,
    usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.generar(datos, usuario)


# --- Escenario 3: alertas (declaradas antes de /{id} para que no las capture) ---


@router.get(
    "/alertas",
    response_model=ListarAlertasRecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Paquetes sin recorrido (HU10 Escenario 3)",
)
async def listar_alertas(
    sucursal_id: int | None = Query(None, gt=0, description="Sucursal donde está el paquete."),
    incluir_resueltas: bool = Query(False),
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.listar_alertas(sucursal_id=sucursal_id, incluir_resueltas=incluir_resueltas)


@router.patch(
    "/alertas/{id}/resolver",
    response_model=AlertaRecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Marcar una alerta como resuelta",
    description="Para alertas atendidas por fuera del sistema. Si el paquete sigue sin recorrido, la próxima "
    "generación o edición vuelve a alertarlo.",
)
async def resolver_alerta(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.resolver_alerta(id)


# --- Escenario 2: visualización ---


@router.get(
    "",
    response_model=ListarRecorridosResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar recorridos",
)
async def listar_recorridos(
    sucursal_id: int | None = Query(None, gt=0),
    fecha: date | None = Query(None),
    tipo_distancia: str | None = Query(None, max_length=10, description="CORTA o LARGA."),
    estado: str | None = Query(None, max_length=15, description="GENERADO, EN_EDICION, EN_CURSO o FINALIZADO."),
    repartidor_id: uuid.UUID | None = Query(None),
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.listar(
        sucursal_id=sucursal_id,
        fecha=fecha,
        tipo_distancia=tipo_distancia,
        estado=estado,
        repartidor_id=repartidor_id,
    )


@router.get(
    "/{id}",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Visualizar un recorrido con sus paradas y trazado (HU10 Escenario 2)",
)
async def obtener_recorrido(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.obtener(id)


# --- Escenario 2: edición manual ---


@router.put(
    "/{id}/paquetes",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Editar manualmente la composición y el orden del recorrido (HU10 Escenario 2)",
    description="Reemplaza los paquetes del recorrido por la lista enviada, en ese orden de visita. Permite "
    "agregar, quitar y reordenar. Solo para recorridos `GENERADO` o `EN_EDICION`; el recorrido pasa a "
    "`EN_EDICION`. Devuelve las alertas de paquetes que quedaron sin recorrido.",
)
async def reemplazar_paquetes(
    id: uuid.UUID,
    datos: ReemplazarPaquetesRecorridoRequest,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.reemplazar_paquetes(id, datos)


@router.delete(
    "/{id}/paquetes/{codigo}",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Quitar un paquete del recorrido",
)
async def quitar_paquete(
    id: uuid.UUID,
    codigo: str = Path(..., max_length=40, description="Número de paquete (`PAQ-XXXXXXXXXX`) o UUID."),
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.quitar_paquete(id, codigo)


@router.patch(
    "/{id}/paquetes/{codigo}/ubicacion",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Completar la ubicación de un domicilio sin coordenadas",
    description="Guarda la ubicación en el envío y recalcula sus recorridos sin iniciar, conservando el orden. "
    "Solo admite domicilios sin coordenadas en recorridos de corta distancia. No modifica recorridos en curso.",
)
async def completar_ubicacion_paquete(
    id: uuid.UUID,
    datos: CompletarUbicacionPaqueteRequest,
    codigo: str = Path(..., max_length=40),
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.completar_ubicacion(id, codigo, datos)


@router.post(
    "/{id}/optimizar",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcular el mejor orden de visita del recorrido",
)
async def optimizar_recorrido(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.optimizar(id)


@router.patch(
    "/{id}/repartidor",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Reasignar el recorrido a otro repartidor",
)
async def reasignar_repartidor(
    id: uuid.UUID,
    datos: ReasignarRepartidorRequest,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.reasignar_repartidor(id, datos)


# --- Salida y descarte ---


@router.post(
    "/{id}/iniciar",
    response_model=RecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar el recorrido (los paquetes salen de la sucursal)",
    description="Pasa el recorrido a `EN_CURSO` y cada paquete a `EN_REPARTO` (corta distancia) o "
    "`EN_TRANSITO` (larga), con su fila en el historial de estados. El cambio se ve en el seguimiento "
    "público (HU04). Desde ese momento el recorrido no se edita.",
)
async def iniciar_recorrido(
    id: uuid.UUID,
    usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.iniciar(id, usuario)


@router.delete(
    "/{id}",
    response_model=EliminarRecorridoResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar un recorrido sin iniciar",
    description="Sus paquetes quedan libres y, si no entran en otro recorrido, se alertan.",
)
async def eliminar_recorrido(
    id: uuid.UUID,
    _usuario: UsuarioModel = Depends(requerir_roles(ROLES_LOGISTICA)),
    servicio: IServicioRecorridos = Depends(get_servicio_recorridos),
):
    return await servicio.eliminar(id)
