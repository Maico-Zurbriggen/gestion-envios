from app.domain.rules.paquete_rules import validar_paquete


def test_paquete_valido_no_devuelve_errores():
    errores = validar_paquete(peso_kg=5, largo_cm=40, ancho_cm=30, alto_cm=20)
    assert errores == []


def test_peso_cero_o_negativo_es_invalido():
    for peso in (0, -1):
        errores = validar_paquete(peso_kg=peso, largo_cm=10, ancho_cm=10, alto_cm=10)
        campos = [e["field"] for e in errores]
        assert "peso_kg" in campos


def test_peso_en_el_limite_de_25kg_es_valido():
    errores = validar_paquete(peso_kg=25, largo_cm=10, ancho_cm=10, alto_cm=10)
    assert not any(e["field"] == "peso_kg" for e in errores)


def test_peso_supera_25kg_es_invalido():
    errores = validar_paquete(peso_kg=25.01, largo_cm=10, ancho_cm=10, alto_cm=10)
    assert any(e["field"] == "peso_kg" for e in errores)


def test_dimension_individual_en_el_limite_de_150cm_es_valida():
    errores = validar_paquete(peso_kg=1, largo_cm=150, ancho_cm=1, alto_cm=1)
    assert not any(e["field"] == "largo_cm" for e in errores)


def test_dimension_individual_supera_150cm_es_invalida():
    for campo, kwargs in (
        ("largo_cm", {"largo_cm": 151, "ancho_cm": 1, "alto_cm": 1}),
        ("ancho_cm", {"largo_cm": 1, "ancho_cm": 151, "alto_cm": 1}),
        ("alto_cm", {"largo_cm": 1, "ancho_cm": 1, "alto_cm": 151}),
    ):
        errores = validar_paquete(peso_kg=1, **kwargs)
        assert any(e["field"] == campo for e in errores)


def test_dimension_cero_o_negativa_es_invalida():
    errores = validar_paquete(peso_kg=1, largo_cm=0, ancho_cm=10, alto_cm=10)
    assert any(e["field"] == "largo_cm" for e in errores)


def test_suma_de_dimensiones_en_el_limite_de_250cm_es_valida():
    errores = validar_paquete(peso_kg=1, largo_cm=100, ancho_cm=100, alto_cm=50)
    assert not any(e["field"] == "dimensiones" for e in errores)


def test_suma_de_dimensiones_supera_250cm_es_invalida_aunque_cada_una_sea_valida():
    # Cada dimensión individualmente es <= 150cm, pero la suma supera 250cm.
    errores = validar_paquete(peso_kg=1, largo_cm=100, ancho_cm=100, alto_cm=100)
    assert any(e["field"] == "dimensiones" for e in errores)


def test_multiples_violaciones_simultaneas_se_reportan_todas():
    errores = validar_paquete(peso_kg=30, largo_cm=200, ancho_cm=10, alto_cm=10)
    campos = {e["field"] for e in errores}
    assert "peso_kg" in campos
    assert "largo_cm" in campos
