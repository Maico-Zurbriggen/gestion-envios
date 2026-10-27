"""Envía un mensaje de prueba con los proveedores configurados en `.env`, sin tocar la base.

Uso desde `Back/`:

    .venv/Scripts/python.exe -m app.infrastructure.probar_notificaciones --email tu@correo.com
    .venv/Scripts/python.exe -m app.infrastructure.probar_notificaciones --whatsapp "+54 9 3564 123456"
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.domain.rules.notificacion_rules import (
    armar_email_nuevo_envio,
    armar_enlace_seguimiento,
    armar_whatsapp_nuevo_envio,
)
from app.domain.rules.telefono_rules import normalizar_telefono_whatsapp
from app.infrastructure.email.email_provider import obtener_proveedor_email
from app.infrastructure.whatsapp.whatsapp_provider import obtener_proveedor_whatsapp

TOKEN_PRUEBA = "ENV-PRUEBA0001"


async def _probar(email: str | None, telefono: str | None) -> bool:
    enlace = armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, TOKEN_PRUEBA)
    todo_ok = True
    if email:
        print(f"Email ({settings.EMAIL_PROVIDER}) -> {email}")
        mensaje = armar_email_nuevo_envio(
            es_remitente=True, nombre="Prueba", remitente_nombre="Prueba",
            token=TOKEN_PRUEBA, numeros_paquetes=["PAQ-PRUEBA0001"], enlace=enlace,
        )
        exito, mensaje_id, error = await obtener_proveedor_email().enviar_email(
            destinatario=email, asunto=f"[Prueba] {mensaje.asunto}", cuerpo_texto=mensaje.texto, cuerpo_html=mensaje.html,
        )
        print(f"  {'OK' if exito else 'FALLÓ'}: {mensaje_id or error}")
        todo_ok &= exito
    if telefono:
        numero = normalizar_telefono_whatsapp(telefono, settings.WHATSAPP_CODIGO_PAIS)
        print(f"WhatsApp ({settings.WHATSAPP_PROVIDER}) -> {telefono} (normalizado: {numero and '+' + numero})")
        if numero is None:
            print("  FALLÓ: el teléfono no es un número válido para WhatsApp.")
            return False
        mensaje = armar_whatsapp_nuevo_envio(nombre="Prueba", token=TOKEN_PRUEBA, enlace=enlace)
        exito, mensaje_id, error = await obtener_proveedor_whatsapp().enviar_whatsapp(numero, mensaje)
        print(f"  {'OK' if exito else 'FALLÓ'}: {mensaje_id or error}")
        todo_ok &= exito
    return todo_ok


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prueba los proveedores de email y WhatsApp configurados.")
    parser.add_argument("--email", help="Dirección a la que enviar un correo de prueba.")
    parser.add_argument("--whatsapp", help="Teléfono al que enviar un WhatsApp de prueba.")
    opciones = parser.parse_args(argumentos)
    if not opciones.email and not opciones.whatsapp:
        parser.error("Indicá --email, --whatsapp o ambos.")
    if "mock" in (settings.EMAIL_PROVIDER.lower(), settings.WHATSAPP_PROVIDER.lower()):
        print("Aviso: un proveedor en 'mock' no envía nada real; solo lo registra en el log.")
    return 0 if asyncio.run(_probar(opciones.email, opciones.whatsapp)) else 1


if __name__ == "__main__":
    sys.exit(main())
