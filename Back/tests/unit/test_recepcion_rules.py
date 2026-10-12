"""Tests de las reglas de dominio de recepción en terminal (HU06).

Son tests puros: no tocan la base de datos ni levantan la app.
"""

import uuid

import pytest

from app.domain.constants.estados_logistica import EstadoPaqueteEnum
from app.domain.rules.codigos_rules import generar_numero_paquete
from app.domain.rules.recepcion_rules import (
    es_numero_paquete,
    es_uuid_paquete,
    evaluar_disponibilidad_recepcion,
    normalizar_codigo_escaneado,
    validar_codigo_escaneado,
)

# --- Normalización de lo que emite el lector de código de barras ---


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("PAQ-ZPC5LB48JJ", "PAQ-ZPC5LB48JJ"),
        ("  PAQ-ZPC5LB48JJ  ", "PAQ-ZPC5LB48JJ"),
        ("PAQ-ZPC5LB48JJ\n", "PAQ-ZPC5LB48JJ"),
        ("PAQ-ZPC5LB48JJ\r\n", "PAQ-ZPC5LB48JJ"),
        ("paq-zpc5lb48jj", "PAQ-ZPC5LB48JJ"),
        ("PAQ- ZPC5LB 48JJ", "PAQ-ZPC5LB48JJ"),
        ("", ""),
    ],
)
def test_normalizar_codigo_escaneado_limpia_lo_que_agrega_el_lector(entrada, esperado):
    """El lector puede agregar espacios, Enter final o emitir minúsculas."""
    assert normalizar_codigo_escaneado(entrada) == esperado


def test_normalizar_codigo_escaneado_tolera_valor_vacio_o_nulo():
    """No debe explotar si el campo llega vacío."""
    assert normalizar_codigo_escaneado("") == ""
    assert normalizar_codigo_escaneado(None) == ""  # type: ignore[arg-type]


# --- Reconocimiento del formato ---


def test_es_numero_paquete_acepta_el_formato_que_genera_hu03():
    """El código de barras de la planilla codifica el `numero_paquete` de HU03."""
    for _ in range(20):
        assert es_numero_paquete(generar_numero_paquete())


@pytest.mark.parametrize(
    "codigo",
    [
        "PAQ-SHORT",              # sufijo de menos de 10 caracteres
        "PAQ-DEMASIADOLARGO123",  # sufijo de más de 10 caracteres
        "ENV-ZPC5LB48JJ",         # es un token de seguimiento, no un paquete
        "PAQZPC5LB48JJ",          # sin guion
        "PAQ-ZPC5LB48J-",         # carácter no alfanumérico en el sufijo
        "",
    ],
)
def test_es_numero_paquete_rechaza_formatos_invalidos(codigo):
    assert not es_numero_paquete(codigo)


def test_es_uuid_paquete_acepta_el_id_interno_del_paquete():
    """Se admite el UUID para que el frontend pueda reusar el endpoint sin reescanear."""
    assert es_uuid_paquete(str(uuid.uuid4()).upper())
    assert es_uuid_paquete(str(uuid.uuid4()))


@pytest.mark.parametrize("codigo", ["PAQ-ZPC5LB48JJ", "no-es-un-uuid", ""])
def test_es_uuid_paquete_rechaza_lo_que_no_es_uuid(codigo):
    assert not es_uuid_paquete(codigo)


# --- Validación completa del código escaneado ---


def test_validar_codigo_escaneado_sin_errores_para_numero_de_paquete():
    assert validar_codigo_escaneado("PAQ-ZPC5LB48JJ") == []


def test_validar_codigo_escaneado_sin_errores_para_uuid():
    assert validar_codigo_escaneado(str(uuid.uuid4())) == []


def test_validar_codigo_escaneado_normaliza_antes_de_validar():
    """Un código con Enter y en minúsculas sigue siendo válido."""
    assert validar_codigo_escaneado("  paq-zpc5lb48jj\n") == []


def test_validar_codigo_escaneado_exige_un_codigo():
    errores = validar_codigo_escaneado("   ")
    assert len(errores) == 1
    assert errores[0]["field"] == "codigo"
    assert "código de barras" in errores[0]["message"]


def test_validar_codigo_escaneado_rechaza_formato_desconocido():
    errores = validar_codigo_escaneado("ENV-ZPC5LB48JJ")
    assert len(errores) == 1
    assert errores[0]["field"] == "codigo"
    assert "formato válido" in errores[0]["message"]


# --- Estados que habilitan la recepción ---


@pytest.mark.parametrize("estado", ["Pendiente", EstadoPaqueteEnum.PENDIENTE.value])
def test_evaluar_disponibilidad_recepcion_habilita_paquete_pendiente(estado):
    """HU03 persiste el literal "Pendiente"; el enum se usa desde HU06 en adelante."""
    disponible, motivo = evaluar_disponibilidad_recepcion(estado)
    assert disponible is True
    assert motivo is None


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value,
        EstadoPaqueteEnum.EN_TRANSITO.value,
        EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
        EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        EstadoPaqueteEnum.EN_SUCURSAL.value,
        EstadoPaqueteEnum.EN_REPARTO.value,
    ],
)
def test_evaluar_disponibilidad_recepcion_bloquea_paquete_ya_recibido(estado):
    """Un paquete ya ingresado a la red no se puede volver a recibir."""
    disponible, motivo = evaluar_disponibilidad_recepcion(estado)
    assert disponible is False
    assert motivo is not None
    assert "ya fue recibido" in motivo


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPaqueteEnum.ENTREGADO.value,
        EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
        EstadoPaqueteEnum.RETIRADO.value,
    ],
)
def test_evaluar_disponibilidad_recepcion_bloquea_paquete_con_ciclo_cerrado(estado):
    """Un paquete entregado o retirado no puede reingresar a la terminal."""
    disponible, motivo = evaluar_disponibilidad_recepcion(estado)
    assert disponible is False
    assert motivo is not None
    assert "completó su ciclo" in motivo


def test_evaluar_disponibilidad_recepcion_bloquea_estado_desconocido():
    disponible, motivo = evaluar_disponibilidad_recepcion("ESTADO_INVENTADO")
    assert disponible is False
    assert motivo is not None
    assert "ESTADO_INVENTADO" in motivo


def test_evaluar_disponibilidad_recepcion_tolera_espacios_sobrantes():
    disponible, _ = evaluar_disponibilidad_recepcion("  Pendiente  ")
    assert disponible is True
