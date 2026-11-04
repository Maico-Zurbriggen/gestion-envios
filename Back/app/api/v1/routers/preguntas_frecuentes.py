from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_servicio_preguntas_frecuentes, requerir_roles
from app.application.interfaces.servicio_preguntas_frecuentes import IServicioPreguntasFrecuentes
from app.contracts.preguntas_frecuentes import (
    ActualizarPreguntaFrecuenteRequest,
    CrearPreguntaFrecuenteRequest,
    EliminarPreguntaFrecuenteResponse,
    ListarPreguntasFrecuentesAdminResponse,
    ListarPreguntasFrecuentesResponse,
    PreguntaFrecuenteAdminResponse,
)
from app.domain.constants.roles import RolEnum

router = APIRouter(prefix="/preguntas-frecuentes", tags=["Preguntas frecuentes"])
router_admin = APIRouter(prefix="/admin/preguntas-frecuentes", tags=["Administración - Preguntas frecuentes"])

ROLES_ADMINISTRACION_CONTENIDO = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]
"""Quienes pueden mantener el contenido de la sección. Vendedores y
repartidores no editan contenido público."""


# --- Vista pública (HU08) ---


@router.get(
    "",
    response_model=ListarPreguntasFrecuentesResponse,
    status_code=status.HTTP_200_OK,
    summary="Sección pública de preguntas frecuentes (HU08)",
    description="Devuelve las preguntas frecuentes publicadas, sin autenticación. Admite filtrar por categoría "
    "y buscar por texto libre (sin distinguir mayúsculas ni tildes). `categorias` lista siempre todas las "
    "categorías publicadas para armar los filtros.",
)
async def listar_preguntas_frecuentes(
    categoria: str | None = Query(
        None,
        max_length=80,
        description="Filtra por categoría (sin distinguir mayúsculas ni tildes).",
    ),
    q: str | None = Query(
        None,
        max_length=100,
        description="Búsqueda libre: cada palabra debe aparecer en la pregunta, la respuesta o la categoría.",
    ),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    """Endpoint público de preguntas frecuentes (HU08). Sin autenticación."""
    return await servicio.listar_publicas(categoria=categoria, busqueda=q)


# --- Administración del contenido ---


@router_admin.get(
    "",
    response_model=ListarPreguntasFrecuentesAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todo el contenido de preguntas frecuentes, incluidas las no publicadas",
)
async def listar_preguntas_frecuentes_admin(
    _usuario=Depends(requerir_roles(ROLES_ADMINISTRACION_CONTENIDO)),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    return await servicio.listar_administracion()


@router_admin.get(
    "/{id}",
    response_model=PreguntaFrecuenteAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalle de una pregunta frecuente",
)
async def obtener_pregunta_frecuente(
    id: int = Path(..., gt=0),
    _usuario=Depends(requerir_roles(ROLES_ADMINISTRACION_CONTENIDO)),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    return await servicio.obtener(id)


@router_admin.post(
    "",
    response_model=PreguntaFrecuenteAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una pregunta frecuente",
    description="Rechaza con `409 DUPLICATE_ENTRY` una pregunta ya cargada, aunque difiera en tildes o signos.",
)
async def crear_pregunta_frecuente(
    datos: CrearPreguntaFrecuenteRequest,
    _usuario=Depends(requerir_roles(ROLES_ADMINISTRACION_CONTENIDO)),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    return await servicio.crear(datos)


@router_admin.patch(
    "/{id}",
    response_model=PreguntaFrecuenteAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Modificar parcialmente una pregunta frecuente (texto, categoría, orden o publicación)",
)
async def actualizar_pregunta_frecuente(
    datos: ActualizarPreguntaFrecuenteRequest,
    id: int = Path(..., gt=0),
    _usuario=Depends(requerir_roles(ROLES_ADMINISTRACION_CONTENIDO)),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    return await servicio.actualizar(id, datos)


@router_admin.delete(
    "/{id}",
    response_model=EliminarPreguntaFrecuenteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar una pregunta frecuente",
    description="Para ocultarla sin perderla, conviene `PATCH` con `publicada: false`.",
)
async def eliminar_pregunta_frecuente(
    id: int = Path(..., gt=0),
    _usuario=Depends(requerir_roles(ROLES_ADMINISTRACION_CONTENIDO)),
    servicio: IServicioPreguntasFrecuentes = Depends(get_servicio_preguntas_frecuentes),
):
    return await servicio.eliminar(id)
