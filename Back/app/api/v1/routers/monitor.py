"""Monitor de envíos: tablero, listado y trazabilidad de todos los paquetes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import exigir_sucursal, get_servicio_monitor, get_servicio_plazos, requerir_roles
from app.application.services.servicio_monitor import ServicioMonitor
from app.application.services.servicio_plazos import ServicioPlazos
from app.contracts.monitor import (
    ListadoMonitorResponse,
    PlazosProcesadosResponse,
    ResumenMonitorResponse,
    TrazaPaqueteResponse,
)
from app.domain.constants.roles import RolEnum

router = APIRouter(prefix="/admin/monitor", tags=["Monitor de envíos"])
PERSONAL = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]

ORDEN = Query("movimiento", pattern="^(movimiento|recientes|antiguos)$", description="movimiento, recientes o antiguos.")


def _filtros(
    buscar: str | None = Query(None, max_length=100, description="Paquete, código de seguimiento, personas o destino."),
    grupo: str | None = Query(
        None, max_length=20,
        description="PENDIENTES, EN_DEPOSITO, EN_CAMINO, PARA_RETIRAR, NO_ENTREGADOS, ENTREGADOS, "
        "CON_PROBLEMAS, SIN_RECORRIDO o CON_RECLAMO.",
    ),
    sucursal_id: int | None = Query(None, ge=1, description="Sucursal actual o de destino."),
    tipo_entrega: str | None = Query(None, max_length=10, description="domicilio o sucursal."),
    desde: datetime | None = Query(None, description="Registrados desde (incluido)."),
    hasta: datetime | None = Query(None, description="Registrados hasta (excluido)."),
    orden: str = ORDEN,
) -> dict:
    return {
        "buscar": buscar, "grupo": grupo, "sucursal_id": sucursal_id, "tipo_entrega": tipo_entrega,
        "desde": desde, "hasta": hasta, "orden": orden,
    }


@router.get("/resumen", response_model=ResumenMonitorResponse, summary="Tablero: paquetes por etapa, actividad del día y pendientes")
async def resumen(
    sucursal_id: int | None = Query(None, ge=1, description="Limitar el tablero a una sucursal."),
    usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioMonitor = Depends(get_servicio_monitor),
):
    return await servicio.resumen(sucursal_id=exigir_sucursal(usuario, sucursal_id))


@router.get("/paquetes", response_model=ListadoMonitorResponse, summary="Todos los paquetes con filtros y paginado")
async def listar_paquetes(
    filtros: dict = Depends(_filtros),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioMonitor = Depends(get_servicio_monitor),
):
    exigir_sucursal(usuario, filtros["sucursal_id"])
    return await servicio.listar(**filtros, pagina=pagina, por_pagina=por_pagina)


@router.get(
    "/paquetes/exportar",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
    summary="Exportar el listado filtrado a CSV (hasta 5000 paquetes)",
)
async def exportar_paquetes(
    filtros: dict = Depends(_filtros),
    usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioMonitor = Depends(get_servicio_monitor),
):
    exigir_sucursal(usuario, filtros["sucursal_id"])
    contenido = await servicio.exportar_csv(**filtros)
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="paquetes.csv"', "Cache-Control": "no-store"},
    )


@router.get("/paquetes/{numero_paquete}", response_model=TrazaPaqueteResponse, summary="Trazabilidad completa de un paquete")
async def trazabilidad(
    numero_paquete: str,
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioMonitor = Depends(get_servicio_monitor),
):
    return await servicio.trazabilidad(numero_paquete)


@router.get(
    "/entregas/{evento_id}/firma",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    summary="Firma de quien recibió el paquete",
)
async def firma(
    evento_id: uuid.UUID,
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioMonitor = Depends(get_servicio_monitor),
):
    contenido, tipo = await servicio.firma(evento_id)
    return Response(
        content=contenido,
        media_type=tipo if tipo.startswith("image/") else "image/png",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/procesar-plazos",
    response_model=PlazosProcesadosResponse,
    summary="Revisar ahora los plazos vencidos (registros sin admitir y retiros no realizados)",
)
async def procesar_plazos(
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlazos = Depends(get_servicio_plazos),
):
    return await servicio.procesar()
