import pytest

from app.domain.rules.notificacion_rules import (
    PLANTILLA_NUEVO_ENVIO,
    armar_email_nuevo_envio,
    armar_enlace_seguimiento,
    armar_whatsapp_nuevo_envio,
)
from app.domain.rules.telefono_rules import enmascarar_telefono, normalizar_telefono_whatsapp


@pytest.mark.parametrize(
    ("telefono", "esperado"),
    [
        ("+543564112233", "5493564112233"),
        ("+54 9 3564 11-2233", "5493564112233"),
        ("3564112233", "5493564112233"),
        ("03564 15 445566", "5493564445566"),
        ("011 15 1234-5678", "5491112345678"),
        ("0351 15 123-4567", "5493511234567"),
        ("543564112233", "5493564112233"),
        ("0054 9 3564 112233", "5493564112233"),
        ("+1 415 555 2671", "14155552671"),
        ("+598 99 123 456", "59899123456"),
    ],
)
def test_normaliza_telefonos_para_whatsapp(telefono, esperado):
    assert normalizar_telefono_whatsapp(telefono) == esperado


@pytest.mark.parametrize("telefono", [None, "", "   ", "123-456", "+12345"])
def test_rechaza_telefonos_inutilizables(telefono):
    assert normalizar_telefono_whatsapp(telefono) is None


def test_otro_codigo_de_pais_por_defecto():
    assert normalizar_telefono_whatsapp("099 123 456", codigo_pais="598") == "59899123456"


def test_enmascara_telefono():
    assert enmascarar_telefono("5493564112233") == "+54******2233"
    assert enmascarar_telefono("12") == "****"


def test_enlace_de_seguimiento_sin_barra_duplicada():
    assert armar_enlace_seguimiento("http://localhost:5173/", "ENV-ABC") == "http://localhost:5173/seguimiento?token=ENV-ABC"


def test_email_escapa_datos_ingresados_por_usuarios():
    mensaje = armar_email_nuevo_envio(
        es_remitente=False,
        nombre="<script>alert(1)</script>",
        remitente_nombre="Ana <b>",
        token="ENV-ABC",
        numeros_paquetes=["PAQ-1"],
        enlace="http://x/seguimiento?token=ENV-ABC",
    )
    assert "<script>" not in mensaje.html and "&lt;script&gt;" in mensaje.html
    assert "Ana &lt;b&gt;" in mensaje.html
    assert "ENV-ABC" in mensaje.asunto and "ENV-ABC" in mensaje.texto


def test_whatsapp_parametros_sin_saltos_de_linea():
    mensaje = armar_whatsapp_nuevo_envio(nombre="Ana\n  María\tPérez", token="ENV-ABC", enlace="http://x")
    assert mensaje.plantilla == PLANTILLA_NUEVO_ENVIO
    assert mensaje.parametros == ["Ana María Pérez", "ENV-ABC", "http://x"]
    assert "ENV-ABC" in mensaje.texto
