import base64
import struct
import zlib
from datetime import date

import pytest

from app.domain.rules.reparto_rules import decodificar_firma_png, receptor_mayor_de_16


def crear_png(ancho=2, alto=2, pixeles=None):
    def chunk(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))

    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0)
    pixeles = pixeles if pixeles is not None else (b"\x00" + b"\x00\x00\x00\xff" * ancho) * alto
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", cabecera) + chunk(b"IDAT", zlib.compress(pixeles)) + chunk(b"IEND", b"")
    )


@pytest.mark.parametrize(
    ("nacimiento", "valido"),
    [
        (date(2010, 10, 26), False),  # cumple exactamente 16
        (date(2010, 10, 25), True),  # más de 16, aunque todavía no tenga 17
        (date(2010, 10, 27), False),
        (date(2000, 1, 1), True),
        (date(2027, 1, 1), False),
        (date(1800, 1, 1), False),
    ],
)
def test_edad_receptor(nacimiento, valido):
    assert receptor_mayor_de_16(nacimiento, date(2026, 10, 26)) is valido


def test_edad_nacido_29_febrero():
    assert not receptor_mayor_de_16(date(2084, 2, 29), date(2100, 2, 28))
    assert receptor_mayor_de_16(date(2084, 2, 29), date(2100, 3, 1))


def test_firma_png_valida():
    png = crear_png()
    assert decodificar_firma_png(base64.b64encode(png).decode()) == png


@pytest.mark.parametrize(
    "contenido",
    [
        b"",
        b"<svg onload='alert(1)'/>",
        b"\x89PNG\r\n\x1a\n",
        crear_png()[:-1],
        crear_png() + b"extra",
        crear_png(1025),
        crear_png(pixeles=b"incorrecto"),
        crear_png(pixeles=b"\x05" + b"\x00" * 17),
        crear_png()[:25] + b"\x00" * 20 + crear_png()[45:],
        b"x" * (256 * 1024 + 1),
    ],
    ids=["vacia", "svg", "cabecera", "truncada", "sobrante", "dimensiones", "pixeles", "filtro", "crc", "peso"],
)
def test_rechaza_firma_invalida(contenido):
    with pytest.raises(ValueError, match="PNG"):
        decodificar_firma_png(base64.b64encode(contenido).decode())


def test_rechaza_base64_invalido():
    with pytest.raises(ValueError, match="PNG"):
        decodificar_firma_png("no-es-base64")
