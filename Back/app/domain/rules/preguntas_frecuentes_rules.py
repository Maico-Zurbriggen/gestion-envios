"""Reglas de dominio de la sección de preguntas frecuentes (HU08).

Contiene funciones puras, sin I/O, para normalizar categorías y textos, y para
resolver la búsqueda libre que ofrece la vista pública. La búsqueda vive acá
(y no en SQL) porque tiene que ignorar mayúsculas **y tildes** ("envio" debe
encontrar "envío"), algo que SQLite y PostgreSQL resuelven de formas distintas
(`unaccent` es una extensión de Postgres que no existe en SQLite). Con el
volumen de una sección de preguntas frecuentes, filtrar en memoria es trivial.
"""

import re
import unicodedata

CATEGORIA_GENERAL = "General"
"""Categoría con la que se muestran las preguntas que no tienen una asignada."""

LONGITUD_MAXIMA_CATEGORIA = 80
"""Coincide con `preguntas_frecuentes.categoria` (`String(80)`)."""


def normalizar_texto_busqueda(texto: str | None) -> str:
    """Lleva un texto a una forma comparable: minúsculas, sin tildes y con los
    espacios colapsados.

    >>> normalizar_texto_busqueda("  ¿Cómo  RETIRO un envío? ")
    '¿como retiro un envio?'
    """
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def normalizar_categoria(categoria: str | None) -> str | None:
    """Limpia la categoría que carga el administrador.

    Colapsa espacios internos y devuelve `None` si queda vacía, para que
    "Envíos", " Envíos " y "Envíos  " terminen siendo la misma categoría en vez
    de tres secciones distintas en la vista pública.
    """
    if categoria is None:
        return None
    limpia = re.sub(r"\s+", " ", categoria).strip()
    return limpia or None


def categoria_visible(categoria: str | None) -> str:
    """Nombre de categoría que se muestra al público (nunca vacío)."""
    return normalizar_categoria(categoria) or CATEGORIA_GENERAL


def misma_categoria(categoria_a: str | None, categoria_b: str | None) -> bool:
    """Compara dos categorías sin distinguir mayúsculas, tildes ni espacios.

    Es lo que usa el filtro `?categoria=` de la vista pública: el frontend
    puede mandar "envios" y encontrar la categoría "Envíos".
    """
    return normalizar_texto_busqueda(categoria_visible(categoria_a)) == normalizar_texto_busqueda(
        categoria_visible(categoria_b)
    )


def coincide_con_busqueda(
    termino: str | None,
    pregunta: str,
    respuesta: str,
    categoria: str | None = None,
) -> bool:
    """Indica si una pregunta frecuente coincide con la búsqueda libre.

    Cada palabra del término tiene que aparecer en la pregunta, la respuesta o
    la categoría (en cualquier orden), ignorando mayúsculas y tildes. Un
    término vacío coincide con todo.
    """
    palabras = normalizar_texto_busqueda(termino).split()
    if not palabras:
        return True

    texto = normalizar_texto_busqueda(f"{pregunta} {respuesta} {categoria or ''}")
    return all(palabra in texto for palabra in palabras)


def es_pregunta_duplicada(pregunta_nueva: str, preguntas_existentes: list[str]) -> bool:
    """Detecta si ya existe la misma pregunta, aunque difiera en tildes,
    mayúsculas, espacios o signos de interrogación.

    Evita que la sección pública muestre dos veces "¿Cómo retiro mi paquete?" y
    "como retiro mi paquete".
    """
    clave_nueva = _clave_pregunta(pregunta_nueva)
    return any(_clave_pregunta(existente) == clave_nueva for existente in preguntas_existentes)


def _clave_pregunta(pregunta: str) -> str:
    """Forma canónica de una pregunta para detectar duplicados."""
    return normalizar_texto_busqueda(pregunta).strip("¿?¡!. ")
