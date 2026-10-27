"""Composición de los mensajes de notificación (HU05 y aviso de visita de HU12).

Funciones puras: arman el texto de cada canal a partir de datos ya validados.
Los valores ingresados por usuarios (nombres) se escapan en el HTML del correo
y ningún mensaje incluye documentos, teléfonos ni direcciones: solo el token y
el vínculo público de seguimiento, que son los datos que la HU pide compartir.
"""

from dataclasses import dataclass, field
from html import escape

PLANTILLA_NUEVO_ENVIO = "nuevo_envio"
PLANTILLA_VISITA_FALLIDA = "visita_fallida"
"""Claves lógicas que cada proveedor de WhatsApp traduce a su plantilla aprobada."""

MAX_LONGITUD_PARAMETRO_WHATSAPP = 300


@dataclass(frozen=True)
class MensajeEmail:
    asunto: str
    texto: str
    html: str


@dataclass(frozen=True)
class MensajeWhatsApp:
    """`texto` se usa como mensaje libre (sandbox o ventana de 24 h);
    `plantilla` + `parametros` cuando el proveedor tiene una plantilla aprobada."""

    texto: str
    plantilla: str
    parametros: list[str] = field(default_factory=list)


def armar_enlace_seguimiento(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/seguimiento?token={token}"


def _parametro(valor: str) -> str:
    """Meta rechaza parámetros con saltos de línea, tabulaciones o más de 4 espacios seguidos."""
    limpio = " ".join((valor or "").split())
    return limpio[:MAX_LONGITUD_PARAMETRO_WHATSAPP] or "-"


def _boton_html(enlace: str, texto: str) -> str:
    return (
        f"<p><a href=\"{escape(enlace, quote=True)}\" style=\"display:inline-block;padding:10px 20px;"
        f"background:#2563eb;color:#ffffff;text-decoration:none;border-radius:6px;\">{escape(texto)}</a></p>"
        f"<p><small>Enlace directo: {escape(enlace)}</small></p>"
    )


def armar_email_nuevo_envio(
    *,
    es_remitente: bool,
    nombre: str,
    remitente_nombre: str,
    token: str,
    numeros_paquetes: list[str],
    enlace: str,
) -> MensajeEmail:
    paquetes = ", ".join(numeros_paquetes) if numeros_paquetes else "Sin paquetes especificados"
    if es_remitente:
        asunto = f"Confirmación de envío - Código de seguimiento: {token}"
        introduccion = "Tu envío fue registrado con éxito en nuestro sistema."
        boton = "Ver seguimiento"
    else:
        asunto = f"Tenés un paquete en camino - Código de seguimiento: {token}"
        introduccion = f"{remitente_nombre} te envió un paquete a través de nuestra red de envíos."
        boton = "Rastrear mi paquete"

    texto = (
        f"Hola {nombre},\n\n"
        f"{introduccion}\n\n"
        f"Código de seguimiento: {token}\n"
        f"Paquetes: {paquetes}\n\n"
        f"Podés consultar el estado del envío en cualquier momento desde este enlace:\n"
        f"{enlace}\n\n"
        f"Gracias por elegir nuestro servicio de logística y distribución."
    )
    html = (
        f"<h2>¡Hola {escape(nombre)}!</h2>"
        f"<p>{escape(introduccion)}</p>"
        f"<p><strong>Código de seguimiento:</strong> <code>{escape(token)}</code></p>"
        f"<p><strong>Paquetes:</strong> {escape(paquetes)}</p>"
        f"{_boton_html(enlace, boton)}"
    )
    return MensajeEmail(asunto=asunto, texto=texto, html=html)


def armar_whatsapp_nuevo_envio(*, nombre: str, token: str, enlace: str) -> MensajeWhatsApp:
    texto = (
        f"Hola {_parametro(nombre)}, se registró un envío en Gestión de Envíos.\n"
        f"Código de seguimiento: {token}\n"
        f"Consultá su estado en: {enlace}"
    )
    return MensajeWhatsApp(
        texto=texto,
        plantilla=PLANTILLA_NUEVO_ENVIO,
        parametros=[_parametro(nombre), _parametro(token), _parametro(enlace)],
    )


def armar_email_visita_fallida(
    *, nombre: str, numero_paquete: str, fecha_hora: str, enlace: str
) -> MensajeEmail:
    texto = (
        f"Hola {nombre},\n\n"
        f"No pudimos concretar la entrega del paquete {numero_paquete}.\n"
        f"Fecha y hora de la visita (UTC): {fecha_hora}.\n"
        f"Consultá el estado de tu envío: {enlace}\n"
    )
    html = (
        f"<h2>Hola {escape(nombre)}</h2>"
        f"<p>No pudimos concretar la entrega del paquete <strong>{escape(numero_paquete)}</strong>.</p>"
        f"<p>Fecha y hora de la visita (UTC): {escape(fecha_hora)}.</p>"
        f"{_boton_html(enlace, 'Consultar el envío')}"
    )
    return MensajeEmail(asunto="Aviso de visita - Entrega no concretada", texto=texto, html=html)


def armar_whatsapp_visita_fallida(*, nombre: str, numero_paquete: str, enlace: str) -> MensajeWhatsApp:
    texto = (
        f"Hola {_parametro(nombre)}, visitamos tu domicilio pero no pudimos entregar "
        f"el paquete {numero_paquete}.\nConsultá el estado de tu envío en: {enlace}"
    )
    return MensajeWhatsApp(
        texto=texto,
        plantilla=PLANTILLA_VISITA_FALLIDA,
        parametros=[_parametro(nombre), _parametro(numero_paquete), _parametro(enlace)],
    )
