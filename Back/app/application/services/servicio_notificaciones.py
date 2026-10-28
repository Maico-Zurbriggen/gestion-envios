import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from app.application.interfaces.proveedores_mensajeria import IEmailProvider, IWhatsAppProvider
from app.application.interfaces.repositorio_notificaciones import IRepositorioNotificaciones
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.contracts.notificaciones import (
    DatosNotificacionEnvio,
    NotificacionesEnvioData,
    NotificacionesEnvioResponse,
    NotificacionItemData,
)
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
)
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.notificacion_rules import (
    MensajeEmail,
    MensajeWhatsApp,
    armar_email_nuevo_envio,
    armar_email_visita_fallida,
    armar_enlace_seguimiento,
    armar_whatsapp_nuevo_envio,
    armar_whatsapp_visita_fallida,
)
from app.domain.rules.plantillas_correo import (
    CAMPOS_CONFIGURACION,
    CAMPOS_PLANTILLA,
    NUEVO_ENVIO_DESTINATARIO,
    NUEVO_ENVIO_REMITENTE,
    VISITA_FALLIDA,
)
from app.domain.rules.telefono_rules import normalizar_telefono_whatsapp
from app.infrastructure.repositories.repositorio_notificaciones import RepositorioNotificaciones
from app.infrastructure.repositories.repositorio_plantillas_correo import RepositorioPlantillasCorreo

MAX_ERROR_DETALLE = 1000
NOMBRE_CANAL = {CanalNotificacionEnum.EMAIL.value: "email", CanalNotificacionEnum.WHATSAPP.value: "WhatsApp"}


def _fecha_local(momento: datetime) -> str:
    """Fecha y hora de Argentina (UTC-3) para mostrar en los correos."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")


def _destino_whatsapp(telefono: str | None) -> str:
    """Se audita el número al que realmente se envía; si no es válido, el original para poder corregirlo."""
    numero = normalizar_telefono_whatsapp(telefono, settings.WHATSAPP_CODIGO_PAIS)
    return f"+{numero}" if numero else (telefono or "")


class ServicioNotificaciones(IServicioNotificaciones):
    """Notificaciones por email y WhatsApp (HU05 y aviso de visita de HU12).

    Cada canal y destinatario es una fila auditada en `notificaciones_envio`.
    Un fallo de un canal no afecta a los demás ni al alta del envío. Un intento
    ya enviado nunca se repite: reintentar solo despacha lo pendiente o fallido,
    y la reserva atómica del repositorio impide dos despachos simultáneos.
    """

    def __init__(
        self,
        email_provider: IEmailProvider,
        session_factory: Callable[[], Any] | None = None,
        repo_notificaciones: IRepositorioNotificaciones | None = None,
        whatsapp_provider: IWhatsAppProvider | None = None,
    ):
        self.email_provider = email_provider
        self.whatsapp_provider = whatsapp_provider
        self.session_factory = session_factory
        self.repo_notificaciones = repo_notificaciones

    @asynccontextmanager
    async def _repositorio(self) -> AsyncIterator[IRepositorioNotificaciones | None]:
        """Las tareas en segundo plano abren su propia sesión: la del request ya se cerró."""
        if self.session_factory:
            async with self.session_factory() as session:
                yield RepositorioNotificaciones(session)
        else:
            yield self.repo_notificaciones

    async def _textos_correo(self) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
        """Plantillas editadas y datos de la empresa. Ante cualquier problema se
        usan los textos de fábrica: un aviso nunca deja de salir por esto."""
        if not self.session_factory:
            return {}, {}
        try:
            async with self.session_factory() as session:
                repo = RepositorioPlantillasCorreo(session)
                plantillas = {
                    clave: {campo: getattr(fila, campo) for campo in CAMPOS_PLANTILLA}
                    for clave, fila in (await repo.obtener_plantillas()).items()
                }
                fila = await repo.obtener_configuracion()
                configuracion = {campo: getattr(fila, campo) or "" for campo in CAMPOS_CONFIGURACION} if fila else {}
                return plantillas, configuracion
        except Exception:
            logger.exception("No se pudieron leer las plantillas de correo; se usan las de fábrica.")
            return {}, {}

    def _canal_habilitado(self, canal: str) -> bool:
        return canal == CanalNotificacionEnum.EMAIL.value or self.whatsapp_provider is not None

    # --- Aviso de visita fallida (HU12) ---

    async def notificar_visita_fallida(self, evento_id: uuid.UUID) -> None:
        """Despacha los avisos ya persistidos, sin deshacer la visita si falla un canal.

        Una repetición permite recuperar un aviso pendiente/fallido. La reserva
        atómica del repositorio impide dos despachos simultáneos del mismo aviso.
        """
        try:
            async with self._repositorio() as repo:
                if repo is None:
                    logger.warning("[ServicioNotificaciones] Sin repositorio para el aviso de visita %s.", evento_id)
                    return
                plantillas, configuracion = await self._textos_correo()
                for aviso in await repo.obtener_avisos_visita(evento_id):
                    if not self._canal_habilitado(aviso.canal) or not await repo.tomar_notificacion(aviso.id):
                        continue
                    evento, envio = aviso.evento_entrega, aviso.envio
                    enlace = armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, envio.token_seguimiento)
                    numero = evento.paquete.numero_paquete
                    contenido: MensajeEmail | MensajeWhatsApp
                    if aviso.canal == CanalNotificacionEnum.EMAIL.value:
                        contenido = armar_email_visita_fallida(
                            nombre=envio.destinatario_nombre,
                            numero_paquete=numero,
                            fecha_hora=_fecha_local(evento.created_at),
                            enlace=enlace,
                            token=envio.token_seguimiento,
                            plantilla=plantillas.get(VISITA_FALLIDA),
                            configuracion=configuracion,
                        )
                    else:
                        contenido = armar_whatsapp_visita_fallida(
                            nombre=envio.destinatario_nombre, numero_paquete=numero, enlace=enlace
                        )
                    await self._enviar_y_finalizar(repo, aviso, contenido, "el aviso de visita")
        except Exception:
            logger.exception("No se pudo procesar el aviso de visita %s; la visita permanece registrada.", evento_id)

    # --- Token de seguimiento (HU05) ---

    async def notificar_nuevo_envio(self, datos: DatosNotificacionEnvio) -> list[Any]:
        """Comparte el token por email y WhatsApp con remitente y destinatario, auditando cada intento."""
        logger.info(f"[ServicioNotificaciones] Notificaciones del envío {datos.envio_id} ({datos.token_seguimiento})")
        enlace = armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, datos.token_seguimiento)
        partes = [
            (DestinatarioNotificacionEnum.REMITENTE.value, datos.remitente_nombre, datos.remitente_email,
             datos.remitente_telefono),
            (DestinatarioNotificacionEnum.DESTINATARIO.value, datos.destinatario_nombre, datos.destinatario_email,
             datos.destinatario_telefono),
        ]
        canales = [c.value for c in CanalNotificacionEnum if self._canal_habilitado(c.value)]

        try:
            async with self._repositorio() as repo:
                if repo is None:
                    logger.warning("[ServicioNotificaciones] Sin repositorio ni session_factory para auditar.")
                    return []
                plantillas, configuracion = await self._textos_correo()
                existentes = {
                    (n.canal, n.destinatario_tipo): n
                    for n in await repo.obtener_por_envio_id(datos.envio_id)
                    if n.evento_entrega_id is None
                }
                for tipo, nombre, email, telefono in partes:
                    for canal in canales:
                        notificacion = existentes.get((canal, tipo))
                        if notificacion is not None and notificacion.estado == EstadoNotificacionEnum.ENVIADO.value:
                            continue
                        if notificacion is None:
                            destino = email if canal == CanalNotificacionEnum.EMAIL.value else _destino_whatsapp(telefono)
                            notificacion = await repo.registrar_intento(datos.envio_id, canal, tipo, destino or "")
                        if not await repo.tomar_notificacion(notificacion.id):
                            continue
                        contenido: MensajeEmail | MensajeWhatsApp
                        if canal == CanalNotificacionEnum.EMAIL.value:
                            es_remitente = tipo == DestinatarioNotificacionEnum.REMITENTE.value
                            contenido = armar_email_nuevo_envio(
                                es_remitente=es_remitente,
                                nombre=nombre,
                                remitente_nombre=datos.remitente_nombre,
                                destinatario_nombre=datos.destinatario_nombre,
                                token=datos.token_seguimiento,
                                numeros_paquetes=datos.numeros_paquetes,
                                enlace=enlace,
                                plantilla=plantillas.get(NUEVO_ENVIO_REMITENTE if es_remitente else NUEVO_ENVIO_DESTINATARIO),
                                configuracion=configuracion,
                            )
                        else:
                            contenido = armar_whatsapp_nuevo_envio(
                                nombre=nombre, token=datos.token_seguimiento, enlace=enlace
                            )
                        await self._enviar_y_finalizar(repo, notificacion, contenido, "el token de seguimiento")
                return await repo.obtener_por_envio_id(datos.envio_id)
        except Exception:
            logger.exception("No se pudieron procesar las notificaciones del envío %s.", datos.envio_id)
            return []

    async def _enviar_y_finalizar(
        self,
        repo: IRepositorioNotificaciones,
        notificacion: Any,
        contenido: MensajeEmail | MensajeWhatsApp,
        descripcion: str,
    ) -> None:
        """Despacha por el canal de la fila reservada y registra el resultado, aun si el proveedor falla."""
        canal = notificacion.canal
        exito, mensaje_id, error = False, None, None
        try:
            if canal == CanalNotificacionEnum.EMAIL.value and isinstance(contenido, MensajeEmail):
                if not notificacion.destino:
                    error = "El destinatario no tiene un email registrado."
                else:
                    exito, mensaje_id, error = await self.email_provider.enviar_email(
                        destinatario=notificacion.destino,
                        asunto=contenido.asunto,
                        cuerpo_texto=contenido.texto,
                        cuerpo_html=contenido.html,
                    )
            elif self.whatsapp_provider is not None and isinstance(contenido, MensajeWhatsApp):
                numero = normalizar_telefono_whatsapp(notificacion.destino, settings.WHATSAPP_CODIGO_PAIS)
                if numero is None:
                    error = "El teléfono registrado no es un número válido para WhatsApp."
                else:
                    exito, mensaje_id, error = await self.whatsapp_provider.enviar_whatsapp(numero, contenido)
        except Exception:
            # No persistir excepciones del proveedor: pueden contener credenciales o URLs firmadas.
            exito, mensaje_id = False, None
            error = f"Falló el proveedor de {NOMBRE_CANAL.get(canal, canal)} al enviar {descripcion}."
            logger.warning("Falló el proveedor de %s para la notificación %s.", canal, notificacion.id)

        if not exito and not error:
            error = f"No se pudo enviar {descripcion} por {NOMBRE_CANAL.get(canal, canal)}."
        await repo.finalizar_notificacion(
            notificacion.id,
            EstadoNotificacionEnum.ENVIADO.value if exito else EstadoNotificacionEnum.FALLIDO.value,
            mensaje_id if exito else None,
            None if exito else (error or "")[:MAX_ERROR_DETALLE],
        )

    # --- Consulta y reintento para el personal ---

    async def _obtener_envio(self, repo: IRepositorioNotificaciones, token: str) -> Any:
        envio = await repo.obtener_envio_por_token(normalizar_token_seguimiento(token))
        if envio is None:
            raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
        return envio

    async def listar_por_token(self, token: str, mensaje: str | None = None) -> NotificacionesEnvioResponse:
        async with self._repositorio() as repo:
            if repo is None:
                raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
            envio = await self._obtener_envio(repo, token)
            filas = await repo.obtener_por_envio_id(envio.id)
            items = [
                NotificacionItemData(
                    id=fila.id,
                    motivo="VISITA_FALLIDA" if fila.evento_entrega_id else "NUEVO_ENVIO",
                    canal=fila.canal,
                    destinatario_tipo=fila.destinatario_tipo,
                    destino=fila.destino,
                    estado=fila.estado,
                    error_detalle=fila.error_detalle,
                    created_at=fila.created_at,
                    updated_at=fila.updated_at,
                )
                for fila in filas
            ]
            return NotificacionesEnvioResponse(
                message=mensaje,
                data=NotificacionesEnvioData(token_seguimiento=envio.token_seguimiento, notificaciones=items),
            )

    async def reintentar_por_token(self, token: str) -> NotificacionesEnvioResponse:
        """Vuelve a despachar solo los intentos pendientes o fallidos del envío."""
        async with self._repositorio() as repo:
            if repo is None:
                raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
            envio = await self._obtener_envio(repo, token)
            datos = DatosNotificacionEnvio(
                envio_id=envio.id,
                token_seguimiento=envio.token_seguimiento,
                remitente_nombre=envio.remitente_nombre,
                remitente_email=envio.remitente_email,
                remitente_telefono=envio.remitente_telefono,
                destinatario_nombre=envio.destinatario_nombre,
                destinatario_email=envio.destinatario_email,
                destinatario_telefono=envio.destinatario_telefono,
                numeros_paquetes=[p.numero_paquete for p in envio.paquetes],
            )
            eventos_pendientes = {
                fila.evento_entrega_id
                for fila in await repo.obtener_por_envio_id(envio.id)
                if fila.evento_entrega_id and fila.estado != EstadoNotificacionEnum.ENVIADO.value
            }
        await self.notificar_nuevo_envio(datos)
        for evento_id in eventos_pendientes:
            await self.notificar_visita_fallida(evento_id)
        return await self.listar_por_token(token, mensaje="Se reintentaron las notificaciones pendientes o fallidas.")
