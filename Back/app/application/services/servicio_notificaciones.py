import uuid
from typing import Any, Callable, List, Optional

from app.application.interfaces.repositorio_notificaciones import IRepositorioNotificaciones
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.contracts.notificaciones import DatosNotificacionEnvio
from app.core.config import settings
from app.core.logging import logger
from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
)
from app.infrastructure.db.models import NotificacionEnvioModel
from app.infrastructure.email.email_provider import IEmailProvider
from app.infrastructure.repositories.repositorio_notificaciones import RepositorioNotificaciones


class ServicioNotificaciones(IServicioNotificaciones):
    """Implementación del servicio de notificaciones desacoplado y asíncrono (HU05)."""

    def __init__(
        self,
        email_provider: IEmailProvider,
        session_factory: Optional[Callable[[], Any]] = None,
        repo_notificaciones: Optional[IRepositorioNotificaciones] = None,
    ):
        self.email_provider = email_provider
        self.session_factory = session_factory
        self.repo_notificaciones = repo_notificaciones

    async def notificar_visita_fallida(self, evento_id: uuid.UUID) -> None:
        """Despacha el aviso ya persistido, sin deshacer la visita si falla el correo.

        Una repetición permite recuperar un aviso pendiente/fallido. La reserva
        atómica del repositorio impide dos despachos simultáneos del mismo aviso.
        """
        try:
            if self.session_factory:
                async with self.session_factory() as session:
                    await self._enviar_aviso_visita(RepositorioNotificaciones(session), evento_id)
            elif self.repo_notificaciones:
                await self._enviar_aviso_visita(self.repo_notificaciones, evento_id)
        except Exception:
            logger.exception("No se pudo procesar el aviso de visita %s; la visita permanece registrada.", evento_id)

    async def _enviar_aviso_visita(self, repo: IRepositorioNotificaciones, evento_id: uuid.UUID) -> None:
        aviso = await repo.obtener_aviso_visita(evento_id)
        if aviso is None or not await repo.tomar_aviso_visita(aviso.id):
            return
        mensaje_id = None
        try:
            if not aviso.destino:
                exito = False
            else:
                evento, envio = aviso.evento_entrega, aviso.envio
                enlace = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/seguimiento?token={envio.token_seguimiento}"
                texto = (
                    f"Hola {envio.destinatario_nombre},\n\n"
                    f"No pudimos concretar la entrega del paquete {evento.paquete.numero_paquete}.\n"
                    f"Fecha y hora de la visita (UTC): {evento.created_at.isoformat()}.\n"
                    f"Consultá el estado de tu envío: {enlace}\n"
                )
                exito, mensaje_id, _ = await self.email_provider.enviar_email(
                    destinatario=aviso.destino, asunto="Aviso de visita - Entrega no concretada", cuerpo_texto=texto,
                )
        except Exception:
            # No persistir respuestas del proveedor que puedan contener credenciales.
            exito = False
            logger.warning("Falló el proveedor de email para el aviso de visita %s.", evento_id)
        await repo.finalizar_aviso_visita(
            aviso.id, EstadoNotificacionEnum.ENVIADO.value if exito else EstadoNotificacionEnum.FALLIDO.value,
            mensaje_id if exito else None,
            None if exito else "No se pudo enviar el aviso de visita por email.",
        )

    async def notificar_nuevo_envio(self, datos: DatosNotificacionEnvio) -> List[NotificacionEnvioModel]:
        """Envía las notificaciones de tracking por correo al emisor y destinatario y registra auditoría."""
        logger.info(
            f"[ServicioNotificaciones] Iniciando notificaciones para envío {datos.envio_id} "
            f"(Token: {datos.token_seguimiento})"
        )

        resultados: List[NotificacionEnvioModel] = []
        link_seguimiento = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/seguimiento?token={datos.token_seguimiento}"
        paquetes_str = ", ".join(datos.numeros_paquetes) if datos.numeros_paquetes else "Sin paquetes especificados"

        destinatarios_a_procesar = [
            {
                "tipo": DestinatarioNotificacionEnum.REMITENTE.value,
                "email": datos.remitente_email,
                "nombre": datos.remitente_nombre,
                "asunto": f"Confirmación de Envío - Código de seguimiento: {datos.token_seguimiento}",
                "texto": (
                    f"Hola {datos.remitente_nombre},\n\n"
                    f"Tu envío ha sido registrado con éxito en nuestro sistema.\n\n"
                    f"Código de seguimiento: {datos.token_seguimiento}\n"
                    f"Paquetes: {paquetes_str}\n\n"
                    f"Puedes seguir el estado de tu envío en cualquier momento desde el siguiente enlace:\n"
                    f"{link_seguimiento}\n\n"
                    f"Gracias por elegir nuestro servicio de logística y distribución."
                ),
                "html": (
                    f"<h2>¡Hola {datos.remitente_nombre}!</h2>"
                    f"<p>Tu envío ha sido registrado con éxito en el sistema.</p>"
                    f"<p><strong>Código de seguimiento:</strong> <code>{datos.token_seguimiento}</code></p>"
                    f"<p><strong>Paquetes:</strong> {paquetes_str}</p>"
                    f"<p><a href='{link_seguimiento}' style='display:inline-block;padding:10px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;'>Ver Seguimiento en Vivo</a></p>"
                    f"<p><small>Enlace directo: {link_seguimiento}</small></p>"
                ),
            },
            {
                "tipo": DestinatarioNotificacionEnum.DESTINATARIO.value,
                "email": datos.destinatario_email,
                "nombre": datos.destinatario_nombre,
                "asunto": f"Tienes un paquete en camino - Código de seguimiento: {datos.token_seguimiento}",
                "texto": (
                    f"Hola {datos.destinatario_nombre},\n\n"
                    f"{datos.remitente_nombre} te ha enviado un paquete a través de nuestro sistema de distribución.\n\n"
                    f"Código de seguimiento: {datos.token_seguimiento}\n"
                    f"Paquetes: {paquetes_str}\n\n"
                    f"Puedes realizar el seguimiento de tu paquete en cualquier momento aquí:\n"
                    f"{link_seguimiento}\n\n"
                    f"Atentamente,\nEquipo de Envíos"
                ),
                "html": (
                    f"<h2>¡Hola {datos.destinatario_nombre}!</h2>"
                    f"<p><strong>{datos.remitente_nombre}</strong> te ha enviado un paquete a través de nuestra red de envíos.</p>"
                    f"<p><strong>Código de seguimiento:</strong> <code>{datos.token_seguimiento}</code></p>"
                    f"<p><strong>Paquetes:</strong> {paquetes_str}</p>"
                    f"<p><a href='{link_seguimiento}' style='display:inline-block;padding:10px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;'>Rastrear mi paquete</a></p>"
                    f"<p><small>Enlace directo: {link_seguimiento}</small></p>"
                ),
            },
        ]

        # Si tenemos session_factory (para ejecución desacoplada en segundo plano), gestionamos la sesión localmente
        if self.session_factory:
            async with self.session_factory() as session:
                repo = RepositorioNotificaciones(session)
                for item in destinatarios_a_procesar:
                    notif = await self._procesar_envio_notificacion(repo, datos.envio_id, item)
                    resultados.append(notif)
        elif self.repo_notificaciones:
            for item in destinatarios_a_procesar:
                notif = await self._procesar_envio_notificacion(self.repo_notificaciones, datos.envio_id, item)
                resultados.append(notif)
        else:
            logger.warning("[ServicioNotificaciones] No se configuró repositorio ni session_factory para persistir logs.")

        return resultados

    async def _procesar_envio_notificacion(
        self,
        repo: IRepositorioNotificaciones,
        envio_id: uuid.UUID,
        item: dict,
    ) -> NotificacionEnvioModel:
        """Crea el log de auditoría inicial, despacha el correo y actualiza el resultado."""
        notificacion = NotificacionEnvioModel(
            id=uuid.uuid4(),
            envio_id=envio_id,
            canal=CanalNotificacionEnum.EMAIL.value,
            destinatario_tipo=item["tipo"],
            destino=item["email"],
            estado=EstadoNotificacionEnum.PENDIENTE.value,
            proveedor_mensaje_id=None,
            error_detalle=None,
        )

        try:
            notificacion = await repo.registrar(notificacion)
        except Exception as e:
            logger.error(f"[ServicioNotificaciones] Error al guardar registro inicial de notificación: {e}", exc_info=True)

        try:
            exito, mensaje_id, error_detalle = await self.email_provider.enviar_email(
                destinatario=item["email"],
                asunto=item["asunto"],
                cuerpo_texto=item["texto"],
                cuerpo_html=item["html"],
            )

            estado_final = EstadoNotificacionEnum.ENVIADO.value if exito else EstadoNotificacionEnum.FALLIDO.value

            notificacion.estado = estado_final
            notificacion.proveedor_mensaje_id = mensaje_id
            notificacion.error_detalle = error_detalle

            try:
                await repo.actualizar_estado(
                    notificacion_id=notificacion.id,
                    estado=estado_final,
                    proveedor_mensaje_id=mensaje_id,
                    error_detalle=error_detalle,
                )
            except Exception as e:
                logger.error(f"[ServicioNotificaciones] Error al actualizar estado de notificación en BD: {e}", exc_info=True)

        except Exception as e:
            error_msg = f"Excepción no controlada durante el envío de correo: {str(e)}"
            logger.error(error_msg, exc_info=True)
            try:
                await repo.actualizar_estado(
                    notificacion_id=notificacion.id,
                    estado=EstadoNotificacionEnum.FALLIDO.value,
                    error_detalle=error_msg,
                )
            except Exception:
                pass

        return notificacion
