import pytest

from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoRetiroEnum
from app.domain.rules.retiro_rules import (
    evaluar_disponibilidad_retiro,
    validar_requisitos_retiro,
)


def test_evaluar_disponibilidad_estados_validos():
    for estado in [
        EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        EstadoPaqueteEnum.EN_SUCURSAL.value,
        EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
        "Pendiente",
    ]:
        disponible, motivo = evaluar_disponibilidad_retiro(estado)
        assert disponible is True
        assert motivo is None


def test_evaluar_disponibilidad_estados_ya_entregados():
    for estado in [
        EstadoPaqueteEnum.ENTREGADO.value,
        EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
        EstadoPaqueteEnum.RETIRADO.value,
    ]:
        disponible, motivo = evaluar_disponibilidad_retiro(estado)
        assert disponible is False
        assert "previamente" in motivo


def test_evaluar_disponibilidad_estados_en_transito():
    disponible, motivo = evaluar_disponibilidad_retiro(EstadoPaqueteEnum.EN_TRANSITO.value)
    assert disponible is False
    assert "EN_TRANSITO" in motivo


def test_validar_requisitos_titular_exitoso():
    errores = validar_requisitos_retiro(
        tipo_retiro=TipoRetiroEnum.TITULAR.value,
        destinatario_mayor_16=True,
        documento_tipo="DNI",
        documento_numero="40123456",
    )
    assert len(errores) == 0


def test_validar_requisitos_titular_menor_16_falla():
    errores = validar_requisitos_retiro(
        tipo_retiro=TipoRetiroEnum.TITULAR.value,
        destinatario_mayor_16=False,
        documento_tipo="DNI",
        documento_numero="40123456",
    )
    assert len(errores) == 1
    assert errores[0]["field"] == "destinatario_mayor_16"


def test_validar_requisitos_tercero_exitoso():
    errores = validar_requisitos_retiro(
        tipo_retiro=TipoRetiroEnum.TERCERO_AUTORIZADO.value,
        destinatario_mayor_16=True,
        documento_tipo="DNI",
        documento_numero="40123456",
        tercero_datos={
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": True,
            "posee_nota_autorizacion": True,
        },
    )
    assert len(errores) == 0


def test_validar_requisitos_tercero_sin_copia_dni_falla():
    errores = validar_requisitos_retiro(
        tipo_retiro=TipoRetiroEnum.TERCERO_AUTORIZADO.value,
        destinatario_mayor_16=True,
        documento_tipo="DNI",
        documento_numero="40123456",
        tercero_datos={
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": False,
            "posee_nota_autorizacion": True,
        },
    )
    assert len(errores) == 1
    assert errores[0]["field"] == "tercero_autorizado.posee_copia_dni_titular"


def test_validar_requisitos_tercero_sin_nota_autorizacion_falla():
    errores = validar_requisitos_retiro(
        tipo_retiro=TipoRetiroEnum.TERCERO_AUTORIZADO.value,
        destinatario_mayor_16=True,
        documento_tipo="DNI",
        documento_numero="40123456",
        tercero_datos={
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": True,
            "posee_nota_autorizacion": False,
        },
    )
    assert len(errores) == 1
    assert errores[0]["field"] == "tercero_autorizado.posee_nota_autorizacion"
