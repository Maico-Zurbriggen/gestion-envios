"""Tests del armado del destino legible de un envío.

El formateador lo comparten la vista pública de seguimiento (HU04) y la
pantalla de recepción en terminal (HU06).
"""

import pytest

from app.domain.rules.destino_rules import (
    formatear_destino_domicilio,
    formatear_destino_sucursal,
)

# --- Destino a domicilio ---


def test_destino_domicilio_completo():
    assert (
        formatear_destino_domicilio("Calle 50 N° 1234", "La Plata", "Buenos Aires")
        == "Calle 50 N° 1234, La Plata, Buenos Aires"
    )


def test_destino_domicilio_omite_partes_vacias():
    """Un campo faltante no debe dejar una coma suelta ni un 'None' en pantalla."""
    assert formatear_destino_domicilio("Calle 50", None, "Buenos Aires") == "Calle 50, Buenos Aires"
    assert formatear_destino_domicilio("Calle 50", "   ", None) == "Calle 50"


def test_destino_domicilio_sin_datos():
    assert formatear_destino_domicilio(None, None, None) == "Domicilio de destino no informado"


# --- Destino en sucursal ---


def test_destino_sucursal_no_duplica_el_prefijo():
    """El catálogo nombra las sucursales "Sucursal X": concatenar a ciegas
    producía "Sucursal Sucursal X"."""
    assert (
        formatear_destino_sucursal("Sucursal Rosario Sur", "Bv. Oroño 2456", "Rosario", "Santa Fe")
        == "Sucursal Rosario Sur - Bv. Oroño 2456, Rosario, Santa Fe"
    )


def test_destino_sucursal_agrega_el_prefijo_si_falta():
    """Si el nombre no trae el prefijo, se agrega para que el renglón se entienda."""
    assert (
        formatear_destino_sucursal("Rosario Sur", "Bv. Oroño 2456", "Rosario", "Santa Fe")
        == "Sucursal Rosario Sur - Bv. Oroño 2456, Rosario, Santa Fe"
    )


@pytest.mark.parametrize("nombre", ["SUCURSAL Rosario Sur", "sucursal Rosario Sur"])
def test_destino_sucursal_detecta_el_prefijo_sin_distinguir_mayusculas(nombre):
    resultado = formatear_destino_sucursal(nombre, "Bv. Oroño 2456", "Rosario", "Santa Fe")
    assert resultado.lower().count("sucursal") == 1


def test_destino_sucursal_sin_ubicacion_devuelve_solo_el_nombre():
    assert formatear_destino_sucursal("Sucursal Rosario Sur", None, None, None) == "Sucursal Rosario Sur"


def test_destino_sucursal_sin_nombre():
    assert (
        formatear_destino_sucursal(None, "Bv. Oroño 2456", "Rosario", "Santa Fe")
        == "Sucursal de destino no informada"
    )
