import uuid

import pytest

from app.domain.constants.estados_logistica import EstadoReclamoEnum, TipoReclamoEnum
from app.domain.rules.reclamo_rules import (
    DESCRIPCIONES_TIPO_RECLAMO,
    MAX_RECLAMOS_ACTIVOS_POR_ENVIO,
    TRANSICIONES_RECLAMO,
    es_estado_reclamo_valido,
    es_reclamo_duplicado,
    es_tipo_reclamo_valido,
    evaluar_habilitacion_reclamo,
    normalizar_tipo_reclamo,
    validar_contacto_reclamo,
    validar_transicion_reclamo,
)

ABIERTO = EstadoReclamoEnum.ABIERTO.value
EN_REVISION = EstadoReclamoEnum.EN_REVISION.value
RESUELTO = EstadoReclamoEnum.RESUELTO.value
RECHAZADO = EstadoReclamoEnum.RECHAZADO.value


def test_todos_los_tipos_del_enum_tienen_descripcion_publica():
    assert set(DESCRIPCIONES_TIPO_RECLAMO) == {t.value for t in TipoReclamoEnum}


def test_todos_los_estados_del_enum_estan_en_la_maquina_de_estados():
    assert set(TRANSICIONES_RECLAMO) == {e.value for e in EstadoReclamoEnum}


@pytest.mark.parametrize("tipo", ["DEMORA", "danio", " Extravio ", "otro"])
def test_tipos_validos_se_normalizan(tipo):
    assert es_tipo_reclamo_valido(tipo)
    assert normalizar_tipo_reclamo(tipo) in DESCRIPCIONES_TIPO_RECLAMO


@pytest.mark.parametrize("tipo", ["", None, "ROBO", "DAÑO"])
def test_tipos_invalidos(tipo):
    assert not es_tipo_reclamo_valido(tipo)


def test_estado_valido():
    assert es_estado_reclamo_valido("en_revision")
    assert not es_estado_reclamo_valido("CERRADO")


def test_habilitacion_hasta_el_tope_de_reclamos_activos():
    assert evaluar_habilitacion_reclamo(0) == (True, None)
    assert evaluar_habilitacion_reclamo(MAX_RECLAMOS_ACTIVOS_POR_ENVIO - 1)[0] is True

    habilitado, motivo = evaluar_habilitacion_reclamo(MAX_RECLAMOS_ACTIVOS_POR_ENVIO)
    assert habilitado is False
    assert str(MAX_RECLAMOS_ACTIVOS_POR_ENVIO) in motivo


def test_reclamo_duplicado_mismo_tipo_y_mismo_objetivo():
    paquete = uuid.uuid4()
    activos = [("DEMORA", None), ("DANIO", paquete)]

    assert es_reclamo_duplicado("demora", None, activos)
    assert es_reclamo_duplicado("DANIO", paquete, activos)


def test_no_es_duplicado_si_cambia_el_tipo_o_el_paquete():
    paquete = uuid.uuid4()
    activos = [("DEMORA", None), ("DANIO", paquete)]

    assert not es_reclamo_duplicado("DEMORA", paquete, activos)
    assert not es_reclamo_duplicado("DANIO", None, activos)
    assert not es_reclamo_duplicado("DANIO", uuid.uuid4(), activos)
    assert not es_reclamo_duplicado("EXTRAVIO", None, activos)


def test_contacto_exige_email_o_telefono():
    errores = validar_contacto_reclamo(None, "   ")
    assert errores == [{"field": "contacto", "message": errores[0]["message"]}]

    assert validar_contacto_reclamo("ana@test.com", None) == []
    assert validar_contacto_reclamo(None, "+54 9 3564 123456") == []
    assert validar_contacto_reclamo(None, "(0351) 422-1234") == []


def test_contacto_rechaza_telefono_con_letras():
    errores = validar_contacto_reclamo(None, "llamame al 123")
    assert errores[0]["field"] == "contacto_telefono"


def test_contacto_rechaza_telefono_con_pocos_digitos():
    errores = validar_contacto_reclamo(None, "(1) - - 2")
    assert errores[0]["field"] == "contacto_telefono"
    assert "dígitos" in errores[0]["message"]


@pytest.mark.parametrize(
    "actual, nuevo",
    [
        (ABIERTO, EN_REVISION),
        (ABIERTO, RESUELTO),
        (ABIERTO, RECHAZADO),
        (EN_REVISION, RESUELTO),
        (EN_REVISION, RECHAZADO),
    ],
)
def test_transiciones_validas(actual, nuevo):
    assert validar_transicion_reclamo(actual, nuevo, "Se respondió al cliente por correo.") == []


def test_pasar_a_revision_no_exige_resolucion():
    assert validar_transicion_reclamo(ABIERTO, EN_REVISION, None) == []


@pytest.mark.parametrize("cerrado", [RESUELTO, RECHAZADO])
def test_cerrar_exige_resolucion(cerrado):
    errores = validar_transicion_reclamo(ABIERTO, cerrado, "corto")
    assert errores[0]["field"] == "resolucion"


@pytest.mark.parametrize("cerrado", [RESUELTO, RECHAZADO])
def test_reclamo_cerrado_no_admite_cambios(cerrado):
    errores = validar_transicion_reclamo(cerrado, EN_REVISION, "Intento de reabrir el reclamo.")
    assert errores[0]["field"] == "estado"
    assert "cerrado" in errores[0]["message"]


def test_no_se_puede_volver_de_revision_a_abierto():
    errores = validar_transicion_reclamo(EN_REVISION, ABIERTO, None)
    assert "No se puede pasar" in errores[0]["message"]


def test_mismo_estado_y_estado_inexistente():
    assert "ya se encuentra" in validar_transicion_reclamo(ABIERTO, ABIERTO, None)[0]["message"]
    assert "inválido" in validar_transicion_reclamo(ABIERTO, "CERRADO", None)[0]["message"]
