"""Armado del destino de un envío como texto legible.

Varias pantallas muestran "a dónde va" un envío en un único renglón: la vista
pública de seguimiento (HU04) y la pantalla de recepción en terminal (HU06).
El formato vive acá para que todas muestren exactamente lo mismo y no haya que
mantener el string en dos servicios distintos.
"""

PREFIJO_SUCURSAL = "Sucursal"


def formatear_destino_domicilio(
    direccion: str | None,
    ciudad: str | None,
    provincia: str | None,
) -> str:
    """Arma el destino de un envío a domicilio: dirección, ciudad y provincia."""
    partes = [parte for parte in (direccion, ciudad, provincia) if parte and parte.strip()]
    if not partes:
        return "Domicilio de destino no informado"
    return ", ".join(parte.strip() for parte in partes)


def formatear_destino_sucursal(
    nombre: str | None,
    direccion: str | None,
    ciudad: str | None,
    provincia: str | None,
) -> str:
    """Arma el destino de un envío para retiro: sucursal, dirección, ciudad y provincia.

    El prefijo "Sucursal" se agrega solo si el nombre no lo trae ya, porque el
    catálogo las nombra "Sucursal Rosario Sur" y concatenar a ciegas producía
    "Sucursal Sucursal Rosario Sur".
    """
    if not nombre or not nombre.strip():
        return "Sucursal de destino no informada"

    nombre_limpio = nombre.strip()
    if not nombre_limpio.lower().startswith(PREFIJO_SUCURSAL.lower()):
        nombre_limpio = f"{PREFIJO_SUCURSAL} {nombre_limpio}"

    ubicacion = ", ".join(
        parte.strip() for parte in (direccion, ciudad, provincia) if parte and parte.strip()
    )
    if not ubicacion:
        return nombre_limpio
    return f"{nombre_limpio} - {ubicacion}"
