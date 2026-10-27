"""Adaptadores de email y WhatsApp sin red: transporte HTTP y servidor SMTP simulados."""

import json
import smtplib
from urllib.parse import parse_qs

import httpx
import pytest

from app.domain.rules.notificacion_rules import PLANTILLA_NUEVO_ENVIO, MensajeWhatsApp
from app.infrastructure.email import email_provider
from app.infrastructure.email.email_provider import SMTPEmailProvider
from app.infrastructure.whatsapp.whatsapp_provider import MetaWhatsAppProvider, TwilioWhatsAppProvider

MENSAJE = MensajeWhatsApp(texto="Hola, token ENV-ABC", plantilla=PLANTILLA_NUEVO_ENVIO, parametros=["Ana", "ENV-ABC", "http://x"])


def _transporte(respuesta: httpx.Response, capturadas: list[httpx.Request]) -> httpx.MockTransport:
    def manejar(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return respuesta

    return httpx.MockTransport(manejar)


async def test_meta_envia_plantilla_aprobada():
    capturadas: list[httpx.Request] = []
    proveedor = MetaWhatsAppProvider(
        token="tok",
        phone_number_id="123",
        api_version="v21.0",
        idioma="es_AR",
        plantillas={PLANTILLA_NUEVO_ENVIO: "token_seguimiento"},
        transport=_transporte(httpx.Response(200, json={"messages": [{"id": "wamid.X"}]}), capturadas),
    )
    exito, mensaje_id, error = await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    assert (exito, mensaje_id, error) == (True, "wamid.X", None)
    request = capturadas[0]
    assert str(request.url) == "https://graph.facebook.com/v21.0/123/messages"
    assert request.headers["Authorization"] == "Bearer tok"
    cuerpo = json.loads(request.content)
    assert cuerpo["to"] == "5493564112233" and cuerpo["type"] == "template"
    assert cuerpo["template"]["name"] == "token_seguimiento"
    assert cuerpo["template"]["language"] == {"code": "es_AR"}
    assert [p["text"] for p in cuerpo["template"]["components"][0]["parameters"]] == ["Ana", "ENV-ABC", "http://x"]


async def test_meta_sin_plantilla_envia_texto_libre():
    capturadas: list[httpx.Request] = []
    proveedor = MetaWhatsAppProvider(
        token="tok", phone_number_id="123", plantillas={},
        transport=_transporte(httpx.Response(200, json={"messages": [{"id": "wamid.Y"}]}), capturadas),
    )
    assert (await proveedor.enviar_whatsapp("5493564112233", MENSAJE))[0]
    cuerpo = json.loads(capturadas[0].content)
    assert cuerpo["type"] == "text" and cuerpo["text"]["body"] == MENSAJE.texto


async def test_meta_error_no_expone_token():
    capturadas: list[httpx.Request] = []
    error_meta = {"error": {"message": "Recipient phone number not in allowed list", "code": 131030}}
    proveedor = MetaWhatsAppProvider(
        token="EAAG-secreto", phone_number_id="123", plantillas={},
        transport=_transporte(httpx.Response(400, json=error_meta), capturadas),
    )
    exito, mensaje_id, error = await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    assert not exito and mensaje_id is None
    assert "131030" in error and "allowed list" in error and "secreto" not in error


async def test_meta_sin_configuracion_falla_sin_llamar_a_la_red():
    exito, _, error = await MetaWhatsAppProvider(token="", phone_number_id="").enviar_whatsapp("549", MENSAJE)
    assert not exito and "WHATSAPP_META_TOKEN" in error


async def test_meta_error_de_red():
    def caer(request):
        raise httpx.ConnectError("sin red")

    proveedor = MetaWhatsAppProvider(token="t", phone_number_id="1", transport=httpx.MockTransport(caer))
    exito, _, error = await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    assert not exito and "ConnectError" in error


async def test_twilio_sandbox_envia_texto_con_prefijo_whatsapp():
    capturadas: list[httpx.Request] = []
    proveedor = TwilioWhatsAppProvider(
        account_sid="AC1", auth_token="secreto", remitente="+14155238886", content_sids={},
        transport=_transporte(httpx.Response(201, json={"sid": "SM1"}), capturadas),
    )
    exito, mensaje_id, error = await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    assert (exito, mensaje_id, error) == (True, "SM1", None)
    request = capturadas[0]
    assert str(request.url) == "https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json"
    formulario = parse_qs(request.content.decode())
    assert formulario["From"] == ["whatsapp:+14155238886"]
    assert formulario["To"] == ["whatsapp:+5493564112233"]
    assert formulario["Body"] == [MENSAJE.texto]


async def test_twilio_con_content_sid_envia_variables():
    capturadas: list[httpx.Request] = []
    proveedor = TwilioWhatsAppProvider(
        account_sid="AC1", auth_token="t", content_sids={PLANTILLA_NUEVO_ENVIO: "HX1"},
        transport=_transporte(httpx.Response(201, json={"sid": "SM2"}), capturadas),
    )
    await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    formulario = parse_qs(capturadas[0].content.decode())
    assert formulario["ContentSid"] == ["HX1"] and "Body" not in formulario
    assert json.loads(formulario["ContentVariables"][0]) == {"1": "Ana", "2": "ENV-ABC", "3": "http://x"}


async def test_twilio_error_estructurado():
    capturadas: list[httpx.Request] = []
    proveedor = TwilioWhatsAppProvider(
        account_sid="AC1", auth_token="secreto", content_sids={},
        transport=_transporte(httpx.Response(400, json={"code": 63007, "message": "Channel not found"}), capturadas),
    )
    exito, _, error = await proveedor.enviar_whatsapp("5493564112233", MENSAJE)
    assert not exito and "63007" in error and "secreto" not in error


class _SMTPFalso:
    instancias: list["_SMTPFalso"] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port
        self.tls = self.login_con = None
        self.enviados = []
        _SMTPFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.tls = True

    def login(self, usuario, clave):
        if clave == "mala":
            raise smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        self.login_con = usuario

    def send_message(self, mensaje):
        self.enviados.append(mensaje)


@pytest.fixture
def smtp_falso(monkeypatch):
    _SMTPFalso.instancias.clear()
    monkeypatch.setattr(email_provider.smtplib, "SMTP", _SMTPFalso)
    monkeypatch.setattr(email_provider.smtplib, "SMTP_SSL", _SMTPFalso)
    return _SMTPFalso.instancias


async def test_gmail_starttls_remitente_de_la_cuenta_y_message_id(smtp_falso):
    proveedor = SMTPEmailProvider(
        host="smtp.gmail.com", port=587, user="envios@gmail.com", password="app-pass", use_tls=True,
        from_email="", from_name="Gestión de Envíos",
    )
    exito, mensaje_id, error = await proveedor.enviar_email("ana@example.com", "Asunto", "Texto", "<p>Texto</p>")
    assert exito and error is None
    servidor = smtp_falso[0]
    assert (servidor.host, servidor.port, servidor.tls, servidor.login_con) == ("smtp.gmail.com", 587, True, "envios@gmail.com")
    enviado = servidor.enviados[0]
    assert "envios@gmail.com" in enviado["From"]
    assert enviado["Message-ID"] == mensaje_id and mensaje_id.endswith("@gmail.com>")


async def test_smtp_ssl_en_puerto_465(smtp_falso, monkeypatch):
    usados = []

    class _SSL(_SMTPFalso):
        def __init__(self, *args, **kwargs):
            usados.append("ssl")
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(email_provider.smtplib, "SMTP_SSL", _SSL)
    proveedor = SMTPEmailProvider(host="smtp.gmail.com", port=465, user="u@gmail.com", password="p")
    assert (await proveedor.enviar_email("a@b.com", "A", "T"))[0]
    assert usados == ["ssl"] and smtp_falso[0].tls is None


async def test_smtp_credenciales_rechazadas_explica_contrasena_de_aplicacion(smtp_falso):
    proveedor = SMTPEmailProvider(host="smtp.gmail.com", port=587, user="u@gmail.com", password="mala")
    exito, _, error = await proveedor.enviar_email("a@b.com", "A", "T")
    assert not exito and "535" in error and "contraseña de aplicación" in error and "mala" not in error


def test_alias_gmail_completa_host(monkeypatch):
    monkeypatch.setattr(email_provider.settings, "EMAIL_PROVIDER", "gmail")
    monkeypatch.setattr(email_provider.settings, "SMTP_HOST", "localhost")
    proveedor = email_provider._crear_proveedor_configurado()
    assert isinstance(proveedor, SMTPEmailProvider) and proveedor.host == "smtp.gmail.com"
