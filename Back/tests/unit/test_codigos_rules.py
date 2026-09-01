import string

from app.domain.rules.codigos_rules import generar_numero_paquete, generar_token_seguimiento

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
