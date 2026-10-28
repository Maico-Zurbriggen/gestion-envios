"""Personalización de los correos a clientes: textos, datos de la empresa, vista previa y prueba."""

from uuid import UUID

from app.application.interfaces.proveedores_mensajeria import IEmailProvider
from app.application.interfaces.repositorio_plantillas_correo import IRepositorioPlantillasCorreo
from app.contracts.correos import (
    ConfiguracionCorreoData,
    ConfiguracionCorreoResponse,
    EnviarPruebaData,
    EnviarPruebaRequest,
    EnviarPruebaResponse,
    GuardarConfiguracionRequest,
    GuardarPlantillaRequest,
    PlantillaCorreoData,
    PlantillaCorreoResponse,
    PlantillasCorreoData,
    PlantillasCorreoResponse,
    TextosPlantillaData,
    VariablePlantillaData,
    VistaPreviaData,
    VistaPreviaRequest,
    VistaPreviaResponse,
)
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.rules.notificacion_rules import armar_enlace_seguimiento
from app.domain.rules.plantillas_correo import (
    CAMPOS_CONFIGURACION,
    CAMPOS_PLANTILLA,
    CONFIGURACION_DEFECTO,
    DATOS_EJEMPLO,
    DEFINICIONES,
    VISITA_FALLIDA,
    renderizar,
    validar_configuracion,
    validar_plantilla,
)


class ServicioPlantillasCorreo:
    def __init__(self, repositorio: IRepositorioPlantillasCorreo, email_provider: IEmailProvider):
        self.repo = repositorio
        self.email_provider = email_provider

    @staticmethod
    def _definicion(clave: str):
        definicion = DEFINICIONES.get(clave)
        if definicion is None:
            raise NotFoundException("No existe una plantilla de correo con esa clave.")
        return definicion

    @staticmethod
    def _de_fabrica(clave: str) -> dict[str, str]:
        definicion = DEFINICIONES[clave]
        return {campo: getattr(definicion, campo) for campo in CAMPOS_PLANTILLA}

    def _a_dato(self, clave: str, fila) -> PlantillaCorreoData:
        definicion = DEFINICIONES[clave]
        fabrica = self._de_fabrica(clave)
        textos = {campo: (getattr(fila, campo) or "") for campo in CAMPOS_PLANTILLA} if fila else fabrica
        return PlantillaCorreoData(
            clave=clave,
            nombre=definicion.nombre,
            descripcion=definicion.descripcion,
            variables=[VariablePlantillaData(nombre=n, descripcion=d) for n, d in definicion.variables.items()],
            personalizada=fila is not None,
            updated_at=fila.updated_at if fila else None,
            de_fabrica=TextosPlantillaData(**fabrica),
            **textos,
        )

    async def _configuracion(self) -> dict[str, str]:
        fila = await self.repo.obtener_configuracion()
        if fila is None:
            return dict(CONFIGURACION_DEFECTO)
        return {campo: getattr(fila, campo) or "" for campo in CAMPOS_CONFIGURACION}

    async def _configuracion_dato(self) -> ConfiguracionCorreoData:
        fila = await self.repo.obtener_configuracion()
        return ConfiguracionCorreoData(**(await self._configuracion()), updated_at=fila.updated_at if fila else None)

    async def listar(self) -> PlantillasCorreoResponse:
        filas = await self.repo.obtener_plantillas()
        return PlantillasCorreoResponse(data=PlantillasCorreoData(
            plantillas=[self._a_dato(clave, filas.get(clave)) for clave in DEFINICIONES],
            configuracion=await self._configuracion_dato(),
        ))

    async def guardar(self, clave: str, datos: GuardarPlantillaRequest, usuario_id: UUID) -> PlantillaCorreoResponse:
        self._definicion(clave)
        campos = {campo: (getattr(datos, campo) or "").strip() for campo in CAMPOS_PLANTILLA}
        errores = validar_plantilla(clave, campos)
        if errores:
            raise ValidationException(message="Revisá los textos de la plantilla.", errors=errores)
        fila = await self.repo.guardar_plantilla(clave, campos, usuario_id)
        return PlantillaCorreoResponse(data=self._a_dato(clave, fila))

    async def restablecer(self, clave: str) -> PlantillaCorreoResponse:
        self._definicion(clave)
        await self.repo.eliminar_plantilla(clave)
        return PlantillaCorreoResponse(message="Plantilla restablecida a los textos de fábrica.", data=self._a_dato(clave, None))

    async def guardar_configuracion(self, datos: GuardarConfiguracionRequest, usuario_id: UUID) -> ConfiguracionCorreoResponse:
        campos = {campo: (getattr(datos, campo) or "").strip() for campo in CAMPOS_CONFIGURACION}
        errores = validar_configuracion(campos)
        if errores:
            raise ValidationException(message="Revisá los datos de la empresa.", errors=errores)
        await self.repo.guardar_configuracion(campos, usuario_id)
        return ConfiguracionCorreoResponse(data=await self._configuracion_dato())

    async def _renderizar_ejemplo(self, clave: str, datos: VistaPreviaRequest) -> tuple[str, str, str]:
        self._definicion(clave)
        filas = await self.repo.obtener_plantillas()
        vigente = self._a_dato(clave, filas.get(clave))
        textos = {campo: getattr(datos, campo) if getattr(datos, campo) is not None else getattr(vigente, campo) for campo in CAMPOS_PLANTILLA}
        errores = validar_plantilla(clave, textos)
        if errores:
            raise ValidationException(message="Revisá los textos de la plantilla.", errors=errores)
        valores = {**DATOS_EJEMPLO, "enlace": armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, DATOS_EJEMPLO["token"])}
        paquetes = None if clave == VISITA_FALLIDA else DATOS_EJEMPLO["paquetes"].split(", ")
        return renderizar(textos, await self._configuracion(), valores, paquetes=paquetes)

    async def vista_previa(self, clave: str, datos: VistaPreviaRequest) -> VistaPreviaResponse:
        asunto, texto, html = await self._renderizar_ejemplo(clave, datos)
        return VistaPreviaResponse(data=VistaPreviaData(asunto=asunto, texto=texto, html=html))

    async def enviar_prueba(self, clave: str, datos: EnviarPruebaRequest) -> EnviarPruebaResponse:
        asunto, texto, html = await self._renderizar_ejemplo(clave, datos)
        exito, _, _ = await self.email_provider.enviar_email(datos.email, f"[Prueba] {asunto}", texto, html)
        if not exito:
            # El detalle del proveedor no se expone: puede incluir datos de la cuenta de envío.
            raise ValidationException(
                message="No pudimos enviar el correo de prueba. Revisá la dirección o la configuración del correo saliente.",
                errors=[{"field": "email", "message": "El proveedor de correo rechazó el envío de prueba."}],
            )
        return EnviarPruebaResponse(data=EnviarPruebaData(enviado=True, destino=datos.email))
