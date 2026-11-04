"""Composición de los mensajes de notificación (HU05 y aviso de visita de HU12).

Funciones puras: arman el texto de cada canal a partir de datos ya validados.
Los valores ingresados por usuarios (nombres) se escapan en el HTML del correo
y ningún mensaje incluye documentos, teléfonos ni direcciones: solo el token y
el vínculo público de seguimiento, que son los datos que la HU pide compartir.
"""

from dataclasses import dataclass, field

from app.domain.rules.plantillas_correo import (
    CAMPOS_PLANTILLA,
    CONFIGURACION_DEFECTO,
    DEFINICIONES,
    NUEVO_ENVIO_DESTINATARIO,
    NUEVO_ENVIO_REMITENTE,
    VISITA_FALLIDA,
    renderizar,
)

PLANTILLA_NUEVO_ENVIO = "nuevo_envio"
PLANTILLA_AVISO_ESTADO = "aviso_estado"
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


def _plantilla(clave: str) -> dict[str, str]:
    """Textos de la plantilla estándar de ese aviso."""
    definicion = DEFINICIONES[clave]
    return {campo: getattr(definicion, campo) for campo in CAMPOS_PLANTILLA}


def armar_email_nuevo_envio(
    *,
    es_remitente: bool,
    nombre: str,
    remitente_nombre: str,
    token: str,
    numeros_paquetes: list[str],
    enlace: str,
    destinatario_nombre: str = "",
    plazo: str = "10 días",
) -> MensajeEmail:
    """Correo de envío registrado, con su plantilla estándar."""
    clave = NUEVO_ENVIO_REMITENTE if es_remitente else NUEVO_ENVIO_DESTINATARIO
    valores = {
        "nombre": nombre,
        "token": token,
        "enlace": enlace,
        "remitente": remitente_nombre,
        "destinatario": destinatario_nombre or "tu destinatario",
        "paquetes": ", ".join(numeros_paquetes) if numeros_paquetes else "Sin paquetes especificados",
        "cantidad_paquetes": str(len(numeros_paquetes)),
        "plazo": plazo,
    }
    asunto, texto, html = renderizar(
        _plantilla(clave), CONFIGURACION_DEFECTO, valores, paquetes=numeros_paquetes
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
    *,
    nombre: str,
    numero_paquete: str,
    fecha_hora: str,
    enlace: str,
    token: str = "",
    proximo_paso: str = "Consultá el seguimiento para ver los próximos pasos.",
) -> MensajeEmail:
    """Aviso de visita fallida, con su plantilla estándar."""
    valores = {
        "nombre": nombre, "paquete": numero_paquete, "fecha": fecha_hora, "enlace": enlace, "token": token,
        "proximo_paso": proximo_paso,
    }
    asunto, texto, html = renderizar(
        _plantilla(VISITA_FALLIDA), CONFIGURACION_DEFECTO, valores
    )
    return MensajeEmail(asunto=asunto, texto=texto, html=html)


def armar_email_hito(
    *,
    clave: str,
    valores: dict[str, str],
) -> MensajeEmail:
    """Correo de un hito del envío (recibido, en reparto, listo para retirar, entregado...)."""
    asunto, texto, html = renderizar(
        _plantilla(clave), CONFIGURACION_DEFECTO, valores
    )
    return MensajeEmail(asunto=asunto, texto=texto, html=html)


def armar_whatsapp_hito(*, nombre: str, novedad: str, enlace: str) -> MensajeWhatsApp:
    """Un único formato para todos los hitos: así alcanza con una plantilla aprobada en Meta."""
    texto = f"Hola {_parametro(nombre)}, {_parametro(novedad)}\nSeguí tu envío en: {enlace}"
    return MensajeWhatsApp(
        texto=texto,
        plantilla=PLANTILLA_AVISO_ESTADO,
        parametros=[_parametro(nombre), _parametro(novedad), _parametro(enlace)],
    )


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
