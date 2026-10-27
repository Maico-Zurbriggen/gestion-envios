"""Adaptadores de WhatsApp para HU05 (token de seguimiento) y el aviso de visita de HU12.

- `MockWhatsAppProvider`: en memoria, para desarrollo y pruebas.
- `MetaWhatsAppProvider`: WhatsApp Cloud API de Meta. Los mensajes iniciados por
  la empresa requieren una plantilla aprobada; sin plantilla configurada se envía
  texto libre, que Meta solo entrega dentro de la ventana de 24 h de atención.
- `TwilioWhatsAppProvider`: API de mensajes de Twilio. En el sandbox acepta texto
  libre hacia números que se unieron con el código `join`; en producción requiere
  una plantilla (Content SID) aprobada.

Ningún adaptador registra ni devuelve credenciales en `error_detalle`.
"""

import json
import uuid

import httpx

from app.application.interfaces.proveedores_mensajeria import IWhatsAppProvider, ResultadoEnvioMensaje
from app.core.config import settings
from app.core.logging import logger
from app.domain.rules.notificacion_rules import (
    PLANTILLA_NUEVO_ENVIO,
    PLANTILLA_VISITA_FALLIDA,
    MensajeWhatsApp,
)
from app.domain.rules.telefono_rules import enmascarar_telefono

MAX_DETALLE_ERROR = 300


def _detalle_error(proveedor: str, respuesta: httpx.Response) -> str:
    """Extrae el código y mensaje del proveedor sin copiar cabeceras ni la URL autenticada."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = {}
    error = cuerpo.get("error", cuerpo) if isinstance(cuerpo, dict) else {}
    codigo = error.get("code", "") if isinstance(error, dict) else ""
    mensaje = error.get("message", "") if isinstance(error, dict) else ""
    detalle = f"{proveedor} respondió HTTP {respuesta.status_code}"
    if codigo:
        detalle += f" (código {codigo})"
    if mensaje:
        detalle += f": {mensaje}"
    return detalle[:MAX_DETALLE_ERROR]


class MockWhatsAppProvider:
    """Proveedor en memoria: registra los mensajes en lugar de enviarlos."""

    def __init__(self, forzar_error: bool = False, mensaje_error: str | None = None):
        self.mensajes_enviados: list[dict] = []
        self.forzar_error = forzar_error
        self.mensaje_error = mensaje_error

    async def enviar_whatsapp(self, destinatario: str, mensaje: MensajeWhatsApp) -> ResultadoEnvioMensaje:
        if self.forzar_error:
            error = self.mensaje_error or "Error simulado en MockWhatsAppProvider"
            logger.warning(f"[MockWhatsAppProvider] Fallo simulado hacia {enmascarar_telefono(destinatario)}")
            return False, None, error
        mensaje_id = f"mock-wa-{uuid.uuid4().hex[:12]}"
        self.mensajes_enviados.append(
            {
                "mensaje_id": mensaje_id,
                "destinatario": destinatario,
                "texto": mensaje.texto,
                "plantilla": mensaje.plantilla,
                "parametros": list(mensaje.parametros),
            }
        )
        logger.info(f"[MockWhatsAppProvider] Mensaje a {enmascarar_telefono(destinatario)} | ID: {mensaje_id}")
        return True, mensaje_id, None

    def limpiar(self) -> None:
        self.mensajes_enviados.clear()


class DeshabilitadoWhatsAppProvider:
    """Canal apagado explícitamente: cada intento queda auditado como fallido."""

    async def enviar_whatsapp(self, destinatario: str, mensaje: MensajeWhatsApp) -> ResultadoEnvioMensaje:
        return False, None, "El canal WhatsApp está deshabilitado en la configuración (WHATSAPP_PROVIDER)."


class MetaWhatsAppProvider:
    """WhatsApp Cloud API: `POST https://graph.facebook.com/{version}/{phone_number_id}/messages`."""

    URL_BASE = "https://graph.facebook.com"

    def __init__(
        self,
        token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
        idioma: str | None = None,
        plantillas: dict[str, str] | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.token = token if token is not None else settings.WHATSAPP_META_TOKEN
        self.phone_number_id = phone_number_id if phone_number_id is not None else settings.WHATSAPP_META_PHONE_NUMBER_ID
        self.api_version = api_version or settings.WHATSAPP_META_API_VERSION
        self.idioma = idioma or settings.WHATSAPP_META_IDIOMA_PLANTILLA
        self.plantillas = plantillas if plantillas is not None else {
            PLANTILLA_NUEVO_ENVIO: settings.WHATSAPP_META_PLANTILLA_NUEVO_ENVIO,
            PLANTILLA_VISITA_FALLIDA: settings.WHATSAPP_META_PLANTILLA_VISITA_FALLIDA,
        }
        self.timeout = timeout or settings.WHATSAPP_TIMEOUT_SEGUNDOS
        self.transport = transport

    def _cuerpo(self, destinatario: str, mensaje: MensajeWhatsApp) -> dict:
        base = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": destinatario}
        plantilla = self.plantillas.get(mensaje.plantilla, "")
        if plantilla:
            return base | {
                "type": "template",
                "template": {
                    "name": plantilla,
                    "language": {"code": self.idioma},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": valor} for valor in mensaje.parametros],
                        }
                    ],
                },
            }
        return base | {"type": "text", "text": {"preview_url": True, "body": mensaje.texto}}

    async def enviar_whatsapp(self, destinatario: str, mensaje: MensajeWhatsApp) -> ResultadoEnvioMensaje:
        if not self.token or not self.phone_number_id:
            return False, None, "Falta configurar WHATSAPP_META_TOKEN o WHATSAPP_META_PHONE_NUMBER_ID."
        url = f"{self.URL_BASE}/{self.api_version}/{self.phone_number_id}/messages"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as cliente:
                respuesta = await cliente.post(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=self._cuerpo(destinatario, mensaje),
                )
        except httpx.HTTPError as e:
            logger.warning(f"[MetaWhatsAppProvider] Sin respuesta de Meta: {type(e).__name__}")
            return False, None, f"No se pudo contactar a la API de WhatsApp de Meta ({type(e).__name__})."

        if respuesta.is_success:
            try:
                mensaje_id = respuesta.json()["messages"][0]["id"]
            except (ValueError, KeyError, IndexError, TypeError):
                mensaje_id = None
            logger.info(f"[MetaWhatsAppProvider] Mensaje aceptado para {enmascarar_telefono(destinatario)}")
            return True, mensaje_id, None
        detalle = _detalle_error("Meta WhatsApp", respuesta)
        logger.warning(f"[MetaWhatsAppProvider] {detalle}")
        return False, None, detalle


class TwilioWhatsAppProvider:
    """Twilio: `POST https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json`."""

    URL_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        remitente: str | None = None,
        content_sids: dict[str, str] | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.account_sid = account_sid if account_sid is not None else settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token if auth_token is not None else settings.TWILIO_AUTH_TOKEN
        remitente = remitente or settings.TWILIO_WHATSAPP_FROM
        self.remitente = remitente if remitente.startswith("whatsapp:") else f"whatsapp:{remitente}"
        self.content_sids = content_sids if content_sids is not None else {
            PLANTILLA_NUEVO_ENVIO: settings.TWILIO_CONTENT_SID_NUEVO_ENVIO,
            PLANTILLA_VISITA_FALLIDA: settings.TWILIO_CONTENT_SID_VISITA_FALLIDA,
        }
        self.timeout = timeout or settings.WHATSAPP_TIMEOUT_SEGUNDOS
        self.transport = transport

    def _formulario(self, destinatario: str, mensaje: MensajeWhatsApp) -> dict[str, str]:
        datos = {"From": self.remitente, "To": f"whatsapp:+{destinatario}"}
        content_sid = self.content_sids.get(mensaje.plantilla, "")
        if content_sid:
            variables = {str(indice): valor for indice, valor in enumerate(mensaje.parametros, start=1)}
            return datos | {"ContentSid": content_sid, "ContentVariables": json.dumps(variables, ensure_ascii=False)}
        return datos | {"Body": mensaje.texto}

    async def enviar_whatsapp(self, destinatario: str, mensaje: MensajeWhatsApp) -> ResultadoEnvioMensaje:
        if not self.account_sid or not self.auth_token:
            return False, None, "Falta configurar TWILIO_ACCOUNT_SID o TWILIO_AUTH_TOKEN."
        url = f"{self.URL_BASE}/Accounts/{self.account_sid}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as cliente:
                respuesta = await cliente.post(
                    url, auth=(self.account_sid, self.auth_token), data=self._formulario(destinatario, mensaje)
                )
        except httpx.HTTPError as e:
            logger.warning(f"[TwilioWhatsAppProvider] Sin respuesta de Twilio: {type(e).__name__}")
            return False, None, f"No se pudo contactar a la API de Twilio ({type(e).__name__})."

        if respuesta.is_success:
            try:
                mensaje_id = respuesta.json().get("sid")
            except ValueError:
                mensaje_id = None
            logger.info(f"[TwilioWhatsAppProvider] Mensaje aceptado para {enmascarar_telefono(destinatario)}")
            return True, mensaje_id, None
        detalle = _detalle_error("Twilio", respuesta)
        logger.warning(f"[TwilioWhatsAppProvider] {detalle}")
        return False, None, detalle


def _crear_proveedor_configurado() -> IWhatsAppProvider:
    proveedor = settings.WHATSAPP_PROVIDER.strip().lower()
    if proveedor == "meta":
        return MetaWhatsAppProvider()
    if proveedor == "twilio":
        return TwilioWhatsAppProvider()
    if proveedor in ("deshabilitado", "off", "none"):
        return DeshabilitadoWhatsAppProvider()
    return MockWhatsAppProvider()


_whatsapp_provider_instance: IWhatsAppProvider | None = None


def obtener_proveedor_whatsapp() -> IWhatsAppProvider:
    """Fábrica singleton del proveedor de WhatsApp configurado."""
    global _whatsapp_provider_instance
    if _whatsapp_provider_instance is None:
        _whatsapp_provider_instance = _crear_proveedor_configurado()
    return _whatsapp_provider_instance


def establecer_proveedor_whatsapp_personalizado(provider: IWhatsAppProvider | None) -> None:
    """Permite sobrescribir (o reiniciar con `None`) el proveedor en pruebas."""
    global _whatsapp_provider_instance
    _whatsapp_provider_instance = provider
