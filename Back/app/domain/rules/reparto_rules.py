"""Validaciones puras de ubicación y constancia de entrega (HU11/HU12)."""

import base64
import binascii
import struct
import zlib
from datetime import date

MAX_FIRMA_BYTES = 256 * 1024


def receptor_mayor_de_16(nacimiento: date, hoy: date) -> bool:
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    aniversario_16 = (nacimiento.year + 16, nacimiento.month, nacimiento.day)
    return nacimiento <= hoy and aniversario_16 < (hoy.year, hoy.month, hoy.day) and edad <= 120


def decodificar_firma_png(valor: str) -> bytes:
    """PNG RGB/RGBA de 8 bits, sin entrelazado, hasta 1024² y 256 KiB.

    Verifica estructura, CRC y contenido comprimido; nunca acepta SVG/HTML
    ni confía en un MIME declarado por el cliente.
    """
    try:
        contenido = base64.b64decode(valor, validate=True)
        if not 0 < len(contenido) <= MAX_FIRMA_BYTES or contenido[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError
        pos = 8
        imagen = bytearray()
        ancho = alto = canales = 0
        terminado = False
        while pos < len(contenido):
            largo = struct.unpack(">I", contenido[pos : pos + 4])[0]
            tipo = contenido[pos + 4 : pos + 8]
            fin = pos + 12 + largo
            if fin > len(contenido):
                raise ValueError
            datos = contenido[pos + 8 : fin - 4]
            crc = struct.unpack(">I", contenido[fin - 4 : fin])[0]
            if zlib.crc32(tipo + datos) != crc:
                raise ValueError
            if pos == 8:
                if tipo != b"IHDR" or largo != 13:
                    raise ValueError
                ancho, alto, bits, color, compresion, filtro, entrelazado = struct.unpack(">IIBBBBB", datos)
                if not (0 < ancho <= 1024 and 0 < alto <= 1024):
                    raise ValueError
                if bits != 8 or color not in (2, 6) or (compresion, filtro, entrelazado) != (0, 0, 0):
                    raise ValueError
                canales = 3 if color == 2 else 4
            elif tipo == b"IHDR":
                raise ValueError
            elif tipo == b"IDAT":
                imagen.extend(datos)
            elif tipo == b"IEND":
                if largo or fin != len(contenido):
                    raise ValueError
                terminado = True
                break
            elif tipo[:1].isupper() and tipo != b"PLTE":
                raise ValueError
            pos = fin
        if not terminado or not imagen:
            raise ValueError
        esperado = alto * (1 + ancho * canales)
        descompresor = zlib.decompressobj()
        pixeles = descompresor.decompress(bytes(imagen), esperado + 1)
        if len(pixeles) != esperado or not descompresor.eof or descompresor.unused_data:
            raise ValueError
        if any(pixeles[fila * (1 + ancho * canales)] > 4 for fila in range(alto)):
            raise ValueError
        return contenido
    except (ValueError, binascii.Error, struct.error, zlib.error) as exc:
        raise ValueError("La firma debe ser un PNG RGB/RGBA válido en base64 (máximo 256 KiB y 1024×1024).") from exc
