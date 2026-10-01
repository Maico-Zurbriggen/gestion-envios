import asyncio
from email.message import EmailMessage
import smtplib
from typing import Optional, Protocol
import uuid

from app.core.config import settings
from app.core.logging import logger


class IEmailProvider(Protocol):
    """Protocolo abstracto para proveedores de envío de correo electrónico."""

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Envía un correo electrónico.
        
        Retorna:
            (exito: bool, proveedor_mensaje_id: Optional[str], error_detalle: Optional[str])
        """
        ...


class MockEmailProvider:
    """Proveedor mock en memoria para desarrollo local y tests automatizados."""

    def __init__(self, forzar_error: bool = False, mensaje_error: Optional[str] = None):
        self.mensajes_enviados: list[dict] = []
        self.forzar_error: bool = forzar_error
        self.mensaje_error: Optional[str] = mensaje_error

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        if self.forzar_error:
            error = self.mensaje_error or "Error simulado en MockEmailProvider"
            logger.warning(f"[MockEmailProvider] Fallo simulado enviando a {destinatario}: {error}")
            return False, None, error

        mensaje_id = f"mock-msg-{uuid.uuid4().hex[:12]}"
        registro = {
            "mensaje_id": mensaje_id,
            "destinatario": destinatario,
            "asunto": asunto,
            "cuerpo_texto": cuerpo_texto,
            "cuerpo_html": cuerpo_html,
        }
        self.mensajes_enviados.append(registro)
        logger.info(
            f"[MockEmailProvider] Correo enviado exitosamente a {destinatario} | "
            f"Asunto: '{asunto}' | ID: {mensaje_id}"
        )
        return True, mensaje_id, None

    def limpiar(self) -> None:
        self.mensajes_enviados.clear()


class SMTPEmailProvider:
    """Proveedor real de correo electrónico vía SMTP configurable por variables de entorno."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.from_email = from_email or settings.SMTP_FROM_EMAIL
        self.from_name = from_name or settings.SMTP_FROM_NAME

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Envía el correo mediante smtplib delegando la operación bloqueante a un thread worker."""
        return await asyncio.to_thread(
            self._enviar_sync, destinatario, asunto, cuerpo_texto, cuerpo_html
        )

    def _enviar_sync(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        try:
            msg = EmailMessage()
            msg["Subject"] = asunto
            msg["From"] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
            msg["To"] = destinatario
            msg.set_content(cuerpo_texto)

            if cuerpo_html:
                msg.add_alternative(cuerpo_html, subtype="html")

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)

            mensaje_id = f"smtp-msg-{uuid.uuid4().hex[:12]}"
            logger.info(f"[SMTPEmailProvider] Correo enviado a {destinatario} con asunto '{asunto}'")
            return True, mensaje_id, None
        except Exception as e:
            error_msg = f"Error SMTP al enviar correo a {destinatario}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg


_email_provider_instance: Optional[IEmailProvider] = None


def obtener_proveedor_email() -> IEmailProvider:
    """Fábrica singleton/global del proveedor de correo configurado."""
    global _email_provider_instance
    if _email_provider_instance is None:
        if settings.EMAIL_PROVIDER.lower() == "smtp":
            _email_provider_instance = SMTPEmailProvider()
        else:
            _email_provider_instance = MockEmailProvider()
    return _email_provider_instance


def establecer_proveedor_email_personalizado(provider: IEmailProvider) -> None:
    """Permite sobrescribir el proveedor para pruebas unitarias o de integración."""
    global _email_provider_instance
    _email_provider_instance = provider
