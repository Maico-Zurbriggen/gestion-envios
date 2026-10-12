import pytest

from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoRetiroEnum
from app.domain.rules.retiro_rules import (
    envio_habilita_retiro_en_sucursal,
    evaluar_disponibilidad_retiro,
    paquete_disponible_en_sucursal,
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


# --- HU09: opciones de retiro desde la experiencia pública ---


def test_hu09_envio_a_sucursal_habilita_retiro():
    """HU09 Escenario 1: el envío se gestiona para retiro, no para domicilio."""
    aplica, motivo = envio_habilita_retiro_en_sucursal("sucursal")
    assert aplica is True
    assert motivo is None


def test_hu09_envio_a_domicilio_no_habilita_retiro():
    """Un envío a domicilio no se retira por sucursal: se informa el motivo."""
    aplica, motivo = envio_habilita_retiro_en_sucursal("domicilio")
    assert aplica is False
    assert motivo is not None
    assert "domicilio" in motivo


@pytest.mark.parametrize("tipo_entrega", ["SUCURSAL", "  sucursal  ", "Sucursal"])
def test_hu09_tipo_entrega_se_normaliza(tipo_entrega):
    """La regla no depende de mayúsculas ni espacios sobrantes."""
    aplica, _ = envio_habilita_retiro_en_sucursal(tipo_entrega)
    assert aplica is True


@pytest.mark.parametrize("tipo_entrega", ["", None, "otra_cosa"])
def test_hu09_tipo_entrega_desconocido_no_habilita_retiro(tipo_entrega):
    aplica, motivo = envio_habilita_retiro_en_sucursal(tipo_entrega)
    assert aplica is False
    assert motivo is not None


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        EstadoPaqueteEnum.EN_SUCURSAL.value,
        EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
    ],
)
def test_hu09_paquete_en_sucursal_destino_esta_disponible(estado):
    """Solo si el paquete ya llegó a la sucursal se avisa que se puede retirar."""
    assert paquete_disponible_en_sucursal(estado) is True


@pytest.mark.parametrize(
    "estado",
    [
        "Pendiente",
        EstadoPaqueteEnum.PENDIENTE.value,
        EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value,
        EstadoPaqueteEnum.EN_TRANSITO.value,
        EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
        EstadoPaqueteEnum.RETIRADO.value,
    ],
)
def test_hu09_paquete_que_no_llego_a_sucursal_no_esta_disponible(estado):
    """La vista pública es más estricta que el mostrador de HU13: un paquete
    "Pendiente" todavía no salió de la terminal de origen, así que no se
    anuncia como retirable aunque `evaluar_disponibilidad_retiro` lo acepte."""
    assert paquete_disponible_en_sucursal(estado) is False
