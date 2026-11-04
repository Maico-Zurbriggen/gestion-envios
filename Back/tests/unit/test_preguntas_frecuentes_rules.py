import pytest

from app.domain.rules.preguntas_frecuentes_rules import (
    CATEGORIA_GENERAL,
    categoria_visible,
    coincide_con_busqueda,
    es_pregunta_duplicada,
    misma_categoria,
    normalizar_categoria,
    normalizar_texto_busqueda,
)


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Envío", "envio"),
        ("  ¿Cómo   RETIRO un paquete? ", "¿como retiro un paquete?"),
        ("Ñandú", "nandu"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalizar_texto_busqueda(entrada, esperado):
    assert normalizar_texto_busqueda(entrada) == esperado


def test_normalizar_categoria_colapsa_espacios_y_vacias_son_none():
    assert normalizar_categoria("  Retiro   en sucursal ") == "Retiro en sucursal"
    assert normalizar_categoria("   ") is None
    assert normalizar_categoria(None) is None


def test_categoria_visible_usa_general_si_no_hay_categoria():
    assert categoria_visible(None) == CATEGORIA_GENERAL
    assert categoria_visible("  ") == CATEGORIA_GENERAL
    assert categoria_visible("Envíos") == "Envíos"


def test_misma_categoria_ignora_tildes_mayusculas_y_espacios():
    assert misma_categoria("Envíos", "envios")
    assert misma_categoria(" Retiro  en sucursal", "RETIRO EN SUCURSAL")
    assert misma_categoria(None, "general")
    assert not misma_categoria("Envíos", "Reclamos")


def test_busqueda_vacia_coincide_con_todo():
    assert coincide_con_busqueda(None, "¿Pregunta?", "Respuesta")
    assert coincide_con_busqueda("   ", "¿Pregunta?", "Respuesta")


def test_busqueda_ignora_tildes_y_mayusculas():
    assert coincide_con_busqueda("ENVIO", "¿Cómo registro un envío?", "Desde el formulario.")


def test_busqueda_exige_todas_las_palabras_en_cualquier_orden_y_campo():
    pregunta = "¿Qué necesito para retirar?"
    respuesta = "Presentar el documento de identidad."
    assert coincide_con_busqueda("documento retirar", pregunta, respuesta)
    assert not coincide_con_busqueda("documento domicilio", pregunta, respuesta)


def test_busqueda_considera_la_categoria():
    assert coincide_con_busqueda("reclamos", "¿Cómo inicio uno?", "Desde el seguimiento.", "Reclamos")


def test_pregunta_duplicada_ignora_signos_tildes_y_mayusculas():
    existentes = ["¿Cómo retiro mi paquete?", "¿Qué no puedo enviar?"]
    assert es_pregunta_duplicada("como retiro mi paquete", existentes)
    assert es_pregunta_duplicada("  ¿CÓMO RETIRO MI PAQUETE?  ", existentes)
    assert not es_pregunta_duplicada("¿Cómo retiro mi envío?", existentes)
    assert not es_pregunta_duplicada("Algo nuevo", [])
