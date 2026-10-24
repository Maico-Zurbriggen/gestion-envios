import string

from app.domain.rules.codigos_rules import (
    generar_numero_paquete,
    generar_token_seguimiento,
    normalizar_token_seguimiento,
)

ALFABETO_VALIDO = set(string.ascii_uppercase + string.digits)


def test_generar_token_seguimiento_tiene_prefijo_y_longitud_correctos():
    token = generar_token_seguimiento()
    assert token.startswith("ENV-")
    sufijo = token.removeprefix("ENV-")
    assert len(sufijo) == 10
    assert set(sufijo) <= ALFABETO_VALIDO


def test_generar_numero_paquete_tiene_prefijo_y_longitud_correctos():
    numero = generar_numero_paquete()
    assert numero.startswith("PAQ-")
    sufijo = numero.removeprefix("PAQ-")
    assert len(sufijo) == 10
    assert set(sufijo) <= ALFABETO_VALIDO


def test_generar_token_seguimiento_no_produce_colisiones_en_un_lote():
    tokens = {generar_token_seguimiento() for _ in range(200)}
    assert len(tokens) == 200


def test_generar_numero_paquete_no_produce_colisiones_en_un_lote():
    numeros = {generar_numero_paquete() for _ in range(200)}
    assert len(numeros) == 200


def test_normalizar_token_seguimiento_tolera_minusculas_y_espacios():
    assert normalizar_token_seguimiento("  env-adrz spq90k\n") == "ENV-ADRZSPQ90K"
    assert normalizar_token_seguimiento("ENV-ADRZSPQ90K") == "ENV-ADRZSPQ90K"
    assert normalizar_token_seguimiento(None) == ""


def test_normalizar_token_seguimiento_es_idempotente_con_los_tokens_generados():
    for _ in range(20):
        token = generar_token_seguimiento()
        assert normalizar_token_seguimiento(token) == token
