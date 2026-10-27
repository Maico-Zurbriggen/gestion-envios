import asyncio
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.application.interfaces.proveedores_mensajeria import IEmailProvider, ResultadoEnvioMensaje
from app.core.config import settings
from app.core.logging import logger

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
PUERTO_SMTP_SSL = 465
"""El puerto 465 usa TLS implícito (SMTP_SSL); el 587 negocia STARTTLS."""

REMITENTE_POR_DEFECTO = "notificaciones@gestionenvios.com"


class MockEmailProvider:
    """Proveedor mock en memoria para desarrollo local y tests automatizados."""

    def __init__(self, forzar_error: bool = False, mensaje_error: str | None = None):
        self.mensajes_enviados: list[dict] = []
        self.forzar_error: bool = forzar_error
        self.mensaje_error: str | None = mensaje_error

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: str | None = None,
    ) -> ResultadoEnvioMensaje:
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
    """Proveedor real de correo vía SMTP (Gmail, Outlook, Mailtrap, servidor propio).

    Para Gmail: `smtp.gmail.com`, puerto 587 con STARTTLS (o 465 con SSL) y una
    contraseña de aplicación de la cuenta con verificación en dos pasos.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        timeout: int | None = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.from_email = from_email or settings.SMTP_FROM_EMAIL or self.user or REMITENTE_POR_DEFECTO
        self.from_name = from_name if from_name is not None else settings.SMTP_FROM_NAME
        self.timeout = timeout or settings.SMTP_TIMEOUT_SEGUNDOS

    async def enviar_email(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: str | None = None,
    ) -> ResultadoEnvioMensaje:
        """Envía el correo mediante smtplib delegando la operación bloqueante a un thread worker."""
        return await asyncio.to_thread(self._enviar_sync, destinatario, asunto, cuerpo_texto, cuerpo_html)

    def _armar_mensaje(
        self, destinatario: str, asunto: str, cuerpo_texto: str, cuerpo_html: str | None
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = asunto
        msg["From"] = formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email
        msg["To"] = destinatario
        dominio = self.from_email.rsplit("@", 1)[-1] if "@" in self.from_email else None
        msg["Message-ID"] = make_msgid(domain=dominio)
        msg.set_content(cuerpo_texto)
        if cuerpo_html:
            msg.add_alternative(cuerpo_html, subtype="html")
        return msg

    def _conectar(self) -> smtplib.SMTP:
        contexto = ssl.create_default_context()
        if self.port == PUERTO_SMTP_SSL:
            return smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=contexto)
        servidor = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        if self.use_tls:
            servidor.starttls(context=contexto)
        return servidor

    def _enviar_sync(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: str | None = None,
    ) -> ResultadoEnvioMensaje:
        try:
            msg = self._armar_mensaje(destinatario, asunto, cuerpo_texto, cuerpo_html)
            with self._conectar() as server:
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
            logger.info(f"[SMTPEmailProvider] Correo enviado a {destinatario} con asunto '{asunto}'")
            return True, msg["Message-ID"], None
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[SMTPEmailProvider] Autenticación rechazada por {self.host} (código {e.smtp_code}).")
            return False, None, (
                f"El servidor SMTP rechazó las credenciales (código {e.smtp_code}). "
                "En Gmail se requiere una contraseña de aplicación."
            )
        except smtplib.SMTPRecipientsRefused:
            logger.warning(f"[SMTPEmailProvider] Destinatario rechazado: {destinatario}")
            return False, None, f"El servidor SMTP rechazó el destinatario {destinatario}."
        except (smtplib.SMTPException, OSError) as e:
            logger.error(f"[SMTPEmailProvider] Error enviando a {destinatario}: {type(e).__name__}", exc_info=True)
            return False, None, f"Error SMTP al enviar correo a {destinatario}: {type(e).__name__}: {e}"


def _crear_proveedor_configurado() -> IEmailProvider:
    proveedor = settings.EMAIL_PROVIDER.strip().lower()
    if proveedor == "gmail":
        host = settings.SMTP_HOST if settings.SMTP_HOST not in ("", "localhost") else GMAIL_SMTP_HOST
        return SMTPEmailProvider(host=host, port=settings.SMTP_PORT or GMAIL_SMTP_PORT)
    if proveedor == "smtp":
        return SMTPEmailProvider()
    return MockEmailProvider()


_email_provider_instance: IEmailProvider | None = None


def obtener_proveedor_email() -> IEmailProvider:
    """Fábrica singleton/global del proveedor de correo configurado."""
    global _email_provider_instance
    if _email_provider_instance is None:
        _email_provider_instance = _crear_proveedor_configurado()
    return _email_provider_instance


def establecer_proveedor_email_personalizado(provider: IEmailProvider) -> None:
    """Permite sobrescribir el proveedor para pruebas unitarias o de integración."""
    global _email_provider_instance
    _email_provider_instance = provider
