"""Personalización de los correos a clientes (administrativos y superadministrador)."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_servicio_plantillas_correo, requerir_roles
from app.application.services.servicio_plantillas_correo import ServicioPlantillasCorreo
from app.contracts.correos import (
    ConfiguracionCorreoResponse,
    EnviarPruebaRequest,
    EnviarPruebaResponse,
    GuardarConfiguracionRequest,
    GuardarPlantillaRequest,
    PlantillaCorreoResponse,
    PlantillasCorreoResponse,
    VistaPreviaRequest,
    VistaPreviaResponse,
)
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import UsuarioModel

router = APIRouter(prefix="/admin/correos", tags=["Correos a clientes"])
PERSONAL = [RolEnum.ADMINISTRATIVO, RolEnum.SUPERADMIN]


@router.get("/plantillas", response_model=PlantillasCorreoResponse, summary="Plantillas de correo y datos de la empresa")
async def listar_plantillas(
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.listar()


@router.put("/plantillas/{clave}", response_model=PlantillaCorreoResponse, summary="Guardar los textos de una plantilla")
async def guardar_plantilla(
    clave: str,
    datos: GuardarPlantillaRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.guardar(clave, datos, usuario.id)


@router.delete("/plantillas/{clave}", response_model=PlantillaCorreoResponse, summary="Volver a los textos de fábrica")
async def restablecer_plantilla(
    clave: str,
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.restablecer(clave)


@router.put("/configuracion", response_model=ConfiguracionCorreoResponse, summary="Datos de la empresa que firman los correos")
async def guardar_configuracion(
    datos: GuardarConfiguracionRequest,
    usuario: UsuarioModel = Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.guardar_configuracion(datos, usuario.id)


@router.post(
    "/plantillas/{clave}/vista-previa",
    response_model=VistaPreviaResponse,
    summary="Vista previa con datos de ejemplo (sin guardar)",
)
async def vista_previa(
    clave: str,
    datos: VistaPreviaRequest,
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.vista_previa(clave, datos)


@router.post(
    "/plantillas/{clave}/prueba",
    response_model=EnviarPruebaResponse,
    summary="Enviar un correo de prueba con datos de ejemplo",
)
async def enviar_prueba(
    clave: str,
    datos: EnviarPruebaRequest,
    _usuario=Depends(requerir_roles(PERSONAL)),
    servicio: ServicioPlantillasCorreo = Depends(get_servicio_plantillas_correo),
):
    return await servicio.enviar_prueba(clave, datos)
