"""Plantillas personalizables de los correos a clientes.

Funciones puras. El personal edita textos (asunto, título, mensaje, botón y pie)
y los datos de la empresa; el diseño HTML es fijo y usa la identidad de la marca.
Los textos admiten variables como {nombre} o {token}; todo valor (de la
plantilla o del envío) se escapa antes de ir al HTML, así un texto editado
nunca puede inyectar marcado.
"""

import re
from dataclasses import dataclass
from html import escape

NUEVO_ENVIO_REMITENTE = "NUEVO_ENVIO_REMITENTE"
NUEVO_ENVIO_DESTINATARIO = "NUEVO_ENVIO_DESTINATARIO"
VISITA_FALLIDA = "VISITA_FALLIDA"
CLAVES = (NUEVO_ENVIO_REMITENTE, NUEVO_ENVIO_DESTINATARIO, VISITA_FALLIDA)

CAMPOS_PLANTILLA = ("asunto", "titulo", "mensaje", "texto_boton", "pie")
CAMPOS_CONFIGURACION = ("nombre_marca", "firma", "telefono_contacto", "email_contacto", "sitio_web", "mensaje_legal")
LIMITES = {
    "asunto": 200, "titulo": 150, "mensaje": 2000, "texto_boton": 60, "pie": 600,
    "nombre_marca": 100, "firma": 300, "telefono_contacto": 40, "email_contacto": 150, "sitio_web": 200, "mensaje_legal": 600,
}

VARIABLES_COMUNES = {
    "nombre": "Nombre de quien recibe el correo",
    "token": "Código de seguimiento del envío",
    "enlace": "Enlace al seguimiento público",
    "marca": "Nombre de la empresa",
}


@dataclass(frozen=True)
class DefinicionPlantilla:
    clave: str
    nombre: str
    descripcion: str
    variables: dict[str, str]
    asunto: str
    titulo: str
    mensaje: str
    texto_boton: str
    pie: str


DEFINICIONES: dict[str, DefinicionPlantilla] = {
    NUEVO_ENVIO_REMITENTE: DefinicionPlantilla(
        clave=NUEVO_ENVIO_REMITENTE,
        nombre="Envío registrado · a quien envía",
        descripcion="Se manda al remitente apenas registra el envío.",
        variables={**VARIABLES_COMUNES, "destinatario": "Nombre de quien recibe el paquete", "paquetes": "Códigos de los paquetes",
                   "cantidad_paquetes": "Cantidad de paquetes"},
        asunto="Confirmación de envío - Código de seguimiento: {token}",
        titulo="¡Tu envío ya está registrado!",
        mensaje=("Hola {nombre}, registramos tu envío para {destinatario}.\n\n"
                 "Llevá el paquete con la planilla impresa a cualquiera de nuestras sucursales. "
                 "Con el código de seguimiento podés consultar su estado en todo momento."),
        texto_boton="Ver seguimiento",
        pie="Guardá este correo: el código de seguimiento es la llave para consultar tu envío.",
    ),
    NUEVO_ENVIO_DESTINATARIO: DefinicionPlantilla(
        clave=NUEVO_ENVIO_DESTINATARIO,
        nombre="Paquete en camino · a quien recibe",
        descripcion="Se manda al destinatario cuando se registra un envío para él.",
        variables={**VARIABLES_COMUNES, "remitente": "Nombre de quien envía", "paquetes": "Códigos de los paquetes",
                   "cantidad_paquetes": "Cantidad de paquetes"},
        asunto="Tenés un paquete en camino - Código de seguimiento: {token}",
        titulo="¡Tenés un paquete en camino!",
        mensaje=("Hola {nombre}, {remitente} te envió {cantidad_paquetes} paquete(s) a través de nuestra red de envíos.\n\n"
                 "Te vamos a avisar cuando haya novedades. Mientras tanto, podés seguirlo con tu código."),
        texto_boton="Rastrear mi paquete",
        pie="Si no esperabas este envío, podés ignorar este mensaje.",
    ),
    VISITA_FALLIDA: DefinicionPlantilla(
        clave=VISITA_FALLIDA,
        nombre="Visita fallida · a quien recibe",
        descripcion="Se manda al destinatario cuando el repartidor no pudo concretar la entrega.",
        variables={**VARIABLES_COMUNES, "paquete": "Código del paquete", "fecha": "Fecha y hora de la visita"},
        asunto="Aviso de visita - Entrega no concretada",
        titulo="Pasamos a entregar tu paquete",
        mensaje=("Hola {nombre}, el {fecha} visitamos tu domicilio para entregar el paquete {paquete}, "
                 "pero no pudimos concretar la entrega.\n\n"
                 "Consultá el seguimiento para ver los próximos pasos."),
        texto_boton="Consultar el envío",
        pie="Si necesitás coordinar la entrega, respondé este correo o comunicate con nosotros.",
    ),
}

CONFIGURACION_DEFECTO = {
    "nombre_marca": "Gestión de Envíos",
    "firma": "El equipo de Gestión de Envíos y Distribución",
    "telefono_contacto": "",
    "email_contacto": "",
    "sitio_web": "",
    "mensaje_legal": "Este es un mensaje automático: lo recibís porque figurás en un envío registrado en nuestra red.",
}

DATOS_EJEMPLO = {
    "nombre": "María Sosa",
    "token": "ENV-7K2Q9XWB4M",
    "enlace": "https://envios.ejemplo.com/seguimiento?token=ENV-7K2Q9XWB4M",
    "destinatario": "Jorge Pereyra",
    "remitente": "Camila Torres",
    "paquetes": "PAQ-4D8R2M7KQ1, PAQ-9T3B6X1ZLC",
    "cantidad_paquetes": "2",
    "paquete": "PAQ-4D8R2M7KQ1",
    "fecha": "28/10/2026 15:40",
}

_VARIABLE = re.compile(r"\{([a-z_]+)\}")


def variables_desconocidas(texto: str, permitidas: dict[str, str]) -> list[str]:
    return sorted({nombre for nombre in _VARIABLE.findall(texto or "") if nombre not in permitidas})


def validar_plantilla(clave: str, campos: dict[str, str | None]) -> list[dict[str, str]]:
    """Errores por campo: obligatorios, largo máximo y variables que no existen."""
    definicion = DEFINICIONES[clave]
    errores = []
    for campo in CAMPOS_PLANTILLA:
        valor = (campos.get(campo) or "").strip()
        if not valor and campo != "pie":
            errores.append({"field": campo, "message": "Este texto es obligatorio."})
        elif len(valor) > LIMITES[campo]:
            errores.append({"field": campo, "message": f"Máximo {LIMITES[campo]} caracteres."})
        desconocidas = variables_desconocidas(valor, definicion.variables)
        if desconocidas:
            disponibles = ", ".join("{" + v + "}" for v in definicion.variables)
            errores.append({"field": campo, "message": f"Variable desconocida: {', '.join('{' + v + '}' for v in desconocidas)}. Disponibles: {disponibles}."})
    if "\n" in (campos.get("asunto") or ""):
        errores.append({"field": "asunto", "message": "El asunto debe ser de una sola línea."})
    return errores


def validar_configuracion(campos: dict[str, str | None]) -> list[dict[str, str]]:
    errores = []
    if not (campos.get("nombre_marca") or "").strip():
        errores.append({"field": "nombre_marca", "message": "El nombre de la empresa es obligatorio."})
    for campo in CAMPOS_CONFIGURACION:
        if len((campos.get(campo) or "").strip()) > LIMITES[campo]:
            errores.append({"field": campo, "message": f"Máximo {LIMITES[campo]} caracteres."})
    sitio = (campos.get("sitio_web") or "").strip()
    if sitio and not re.match(r"^https?://[^\s]+$", sitio):
        errores.append({"field": "sitio_web", "message": "Ingresá una dirección que empiece con http:// o https://."})
    return errores


def rellenar(texto: str, valores: dict[str, str]) -> str:
    """Reemplaza {variable} por su valor; las desconocidas quedan tal cual."""
    return _VARIABLE.sub(lambda m: valores.get(m.group(1), m.group(0)), texto or "")


def _parrafos_html(texto: str) -> str:
    bloques = [b.strip() for b in re.split(r"\n\s*\n", texto or "") if b.strip()]
    return "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.65;color:#2f4652;">{escape(b).replace(chr(10), "<br>")}</p>'
        for b in bloques
    )


def renderizar(
    plantilla: dict[str, str], configuracion: dict[str, str], valores: dict[str, str], *, paquetes: list[str] | None = None
) -> tuple[str, str, str]:
    """Devuelve (asunto, texto plano, HTML) con la identidad de la marca.

    El HTML usa tablas y estilos en línea: es lo único que respetan Gmail,
    Outlook y los clientes de correo móviles.
    """
    marca = (configuracion.get("nombre_marca") or CONFIGURACION_DEFECTO["nombre_marca"]).strip()
    valores = {**valores, "marca": marca}
    asunto = " ".join(rellenar(plantilla["asunto"], valores).split())
    titulo = rellenar(plantilla["titulo"], valores)
    mensaje = rellenar(plantilla["mensaje"], valores)
    boton = rellenar(plantilla["texto_boton"], valores)
    pie = rellenar(plantilla.get("pie") or "", valores)
    enlace = valores.get("enlace", "")
    token = valores.get("token", "")
    firma = (configuracion.get("firma") or "").strip()
    contacto = [c for c in (
        (configuracion.get("telefono_contacto") or "").strip(),
        (configuracion.get("email_contacto") or "").strip(),
        (configuracion.get("sitio_web") or "").strip(),
    ) if c]
    legal = (configuracion.get("mensaje_legal") or "").strip()

    texto = "\n\n".join(p for p in (
        titulo, mensaje,
        f"Código de seguimiento: {token}" if token else "",
        f"Paquetes: {', '.join(paquetes)}" if paquetes else "",
        f"{boton}: {enlace}" if enlace else "",
        pie, firma, " · ".join(contacto), legal,
    ) if p)

    filas_paquetes = "".join(
        f'<tr><td style="padding:10px 14px;border-top:1px solid #e6ecef;font-family:Consolas,Menlo,monospace;font-size:13px;color:#0f2a37;">{escape(p)}</td>'
        f'<td style="padding:10px 14px;border-top:1px solid #e6ecef;font-size:12px;color:#66777f;text-align:right;">Paquete {i} de {len(paquetes)}</td></tr>'
        for i, p in enumerate(paquetes or [], start=1)
    )
    bloque_paquetes = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 22px;border:1px solid #dce4e8;border-radius:10px;border-collapse:separate;">'
        '<tr><td colspan="2" style="padding:10px 14px;background:#f7f9fa;border-radius:10px 10px 0 0;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#7d8e97;">Paquetes del envío</td></tr>'
        f"{filas_paquetes}</table>"
    ) if paquetes else ""
    bloque_token = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 22px;">'
        '<tr><td style="padding:16px 18px;background:#fdf5ee;border-left:4px solid #d9701f;border-radius:8px;">'
        '<div style="font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#b85c17;">Código de seguimiento</div>'
        f'<div style="margin-top:6px;font-family:Consolas,Menlo,monospace;font-size:22px;font-weight:700;letter-spacing:.06em;color:#0f2a37;">{escape(token)}</div>'
        "</td></tr></table>"
    ) if token else ""
    bloque_boton = (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:4px 0 10px;"><tr>'
        f'<td style="border-radius:10px;background:#b85c17;"><a href="{escape(enlace, quote=True)}" '
        'style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;">'
        f"{escape(boton)} &rarr;</a></td></tr></table>"
        f'<p style="margin:0 0 20px;font-size:12px;color:#7d8e97;">Si el botón no funciona, copiá este enlace: <a href="{escape(enlace, quote=True)}" style="color:#0f766e;word-break:break-all;">{escape(enlace)}</a></p>'
    ) if enlace else ""
    bloque_pie = f'<p style="margin:0;font-size:13px;line-height:1.6;color:#4a5f6b;">{escape(pie)}</p>' if pie else ""
    bloque_firma = f'<p style="margin:18px 0 0;font-size:14px;font-weight:600;color:#0f2a37;">{escape(firma)}</p>' if firma else ""
    bloque_contacto = (
        f'<p style="margin:0 0 8px;font-size:12px;color:#4a5f6b;">{" &nbsp;·&nbsp; ".join(escape(c) for c in contacto)}</p>'
    ) if contacto else ""
    bloque_legal = f'<p style="margin:0;font-size:11px;line-height:1.5;color:#8a9aa3;">{escape(legal)}</p>' if legal else ""
    previa = escape(" ".join(mensaje.split())[:140])

    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(asunto)}</title></head>
<body style="margin:0;padding:0;background:#eef2f4;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{previa}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f4;font-family:Montserrat,'Segoe UI',Arial,sans-serif;">
<tr><td align="center" style="padding:28px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:22px 28px;background:#0f2a37;border-radius:16px 16px 0 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="width:40px;height:40px;background:#d9701f;border-radius:10px;text-align:center;font-size:20px;line-height:40px;">&#128230;</td>
<td style="padding-left:12px;"><div style="font-size:16px;font-weight:600;color:#ffffff;">{escape(marca)}</div>
<div style="font-size:10px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#efae74;">Envíos y distribución</div></td>
</tr></table></td></tr>
<tr><td style="height:4px;background:#d9701f;line-height:4px;font-size:0;">&nbsp;</td></tr>
<tr><td style="padding:32px 28px 26px;background:#ffffff;">
<h1 style="margin:0 0 16px;font-size:24px;line-height:1.25;font-weight:600;color:#0f2a37;">{escape(titulo)}</h1>
{_parrafos_html(mensaje)}
{bloque_token}{bloque_paquetes}{bloque_boton}{bloque_pie}{bloque_firma}
</td></tr>
<tr><td style="padding:20px 28px 24px;background:#f7f9fa;border-top:1px solid #dce4e8;border-radius:0 0 16px 16px;">
{bloque_contacto}{bloque_legal}
</td></tr>
</table></td></tr></table></body></html>"""
    return asunto, texto, html
