from typing import Protocol

from app.domain.rules.notificacion_rules import MensajeWhatsApp

ResultadoEnvioMensaje = tuple[bool, str | None, str | None]
"""(exito, proveedor_mensaje_id, error_detalle). `error_detalle` nunca debe incluir credenciales."""


class IEmailProvider(Protocol):
    """Puerto de salida para el envío de correos (HU05 y aviso de visita de HU12)."""

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: str | None = None,
    ) -> ResultadoEnvioMensaje: ...


class IWhatsAppProvider(Protocol):
    """Puerto de salida para mensajes de WhatsApp (HU05 y aviso de visita de HU12).

    `destinatario` llega normalizado en E.164 sin `+` (ver `telefono_rules`).
    """

    async def enviar_whatsapp(self, destinatario: str, mensaje: MensajeWhatsApp) -> ResultadoEnvioMensaje: ...
