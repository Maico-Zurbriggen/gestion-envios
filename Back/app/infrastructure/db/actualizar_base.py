"""Mantiene el esquema de cualquier base (SQLite local o Neon) alineado con el código.

La base de Neon es compartida por todo el equipo. Antes, la API creaba las
tablas con `create_all` al arrancar: eso agrega tablas nuevas pero nunca
columnas ni restricciones a tablas existentes, y no registra la versión de
Alembic, así que Neon quedaba desactualizada después de cada cambio de modelo.

Ahora el único camino para cambiar el esquema son las migraciones de Alembic:

- Al arrancar, la API aplica `alembic upgrade head` (`DB_ACTUALIZAR_ESQUEMA_AL_INICIAR`).
- Una base creada con `create_all` (sin tabla `alembic_version`) se adopta:
  se detecta en qué revisión está, se marca y se migra desde ahí.
- En PostgreSQL un candado asesor serializa las migraciones: si dos personas
  arrancan la API a la vez contra Neon, la segunda espera y no repite nada.

Uso manual (desde `Back/`):

    .venv/Scripts/python.exe -m app.infrastructure.db.actualizar_base             # aplica lo pendiente
    .venv/Scripts/python.exe -m app.infrastructure.db.actualizar_base --verificar # solo informa
    .venv/Scripts/python.exe -m app.infrastructure.db.actualizar_base --database-url "postgresql://..." --semillas
"""

import argparse
import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import inspect
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.db.engine_utils import (
    normalizar_url_base_datos,
    obtener_connect_args,
    url_para_migraciones,
)
from app.infrastructure.db.models import Base

DIRECTORIO_MIGRACIONES = Path(__file__).parent / "migrations"

REVISION_INICIAL = "5c87e509d4e7"
REVISION_HU10 = "b7d41e9a2c63"
REVISION_HU11_HU12 = "d2a6f81112ac"
"""Revisiones que pudo haber dejado `create_all` antes de este cambio. Desde
ahora el esquema solo cambia por migraciones, así que la lista no crece."""

REVISION_CORREOS = "539e81c168e2"
REVISION_DESCARGAS = "7f3c2a91d4b8"
TABLAS_SOLO_POR_MIGRACION = {
    "plantillas_correo": REVISION_CORREOS,
    "configuracion_correo": REVISION_CORREOS,
    "controles_descarga": REVISION_DESCARGAS,
    "lecturas_descarga": REVISION_DESCARGAS,
}
"""Tablas nacidas después de `create_all`: una base heredada no las tiene (las
crea la migración). Solo una base armada con los modelos actuales (pruebas) las trae."""


class EsquemaNoAdoptableError(RuntimeError):
    """La base tiene tablas creadas a mano que no corresponden a ninguna revisión conocida."""


@dataclass
class ResultadoActualizacion:
    base: str
    revision_anterior: str | None
    revision_actual: str | None
    revision_head: str
    pendientes: list[str] = field(default_factory=list)
    diferencias: list[str] = field(default_factory=list)

    @property
    def al_dia(self) -> bool:
        return self.revision_actual == self.revision_head


def url_segura(database_url: str) -> str:
    """URL para mostrar en logs y consola, sin la contraseña."""
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<url inválida>"


def resolver_url(database_url: str | None = None) -> str:
    if database_url:
        return url_para_migraciones(database_url)
    return url_para_migraciones(settings.DATABASE_URL, settings.DATABASE_URL_MIGRACIONES)


def configuracion_alembic(database_url: str | None = None) -> Config:
    """Config de Alembic independiente del directorio de trabajo y sin reconfigurar el logging de la app."""
    config = Config()
    config.set_main_option("script_location", str(DIRECTORIO_MIGRACIONES))
    config.set_main_option("path_separator", "os")
    config.attributes["database_url"] = resolver_url(database_url)
    config.attributes["adoptar_base_existente"] = True
    return config


def revision_de_base_heredada(conexion: Connection) -> str | None:
    """Revisión equivalente a una base creada con `create_all`, o `None` si no hay que adoptarla.

    Si existe `alembic_version`, Alembic ya administra la base. Si no hay tablas
    del sistema, es una base vacía y se migra desde cero.
    """
    inspector = inspect(conexion)
    tablas = set(inspector.get_table_names())
    if "alembic_version" in tablas or "usuarios" not in tablas:
        return None

    faltantes = sorted(set(Base.metadata.tables) - tablas - set(TABLAS_SOLO_POR_MIGRACION))
    if faltantes:
        raise EsquemaNoAdoptableError(
            "La base tiene tablas creadas sin Alembic y le faltan: "
            f"{', '.join(faltantes)}. No se puede determinar su revisión: respaldá los datos y "
            "recreá la base, o completala a mano y marcala con `alembic stamp`."
        )

    def columnas(tabla: str) -> set[str]:
        return {columna["name"] for columna in inspector.get_columns(tabla)}

    if set(TABLAS_SOLO_POR_MIGRACION) <= tablas:
        return REVISION_DESCARGAS
    if {"plantillas_correo", "configuracion_correo"} <= tablas:
        return REVISION_CORREOS
    if "procesando_at" in columnas("notificaciones_envio"):
        return REVISION_HU11_HU12
    if "distancia_estimada_km" in columnas("recorridos"):
        return REVISION_HU10
    return REVISION_INICIAL


async def _con_conexion(database_url: str, operacion: Callable[[Connection], Any]) -> Any:
    motor = create_async_engine(database_url, poolclass=NullPool, connect_args=obtener_connect_args(database_url))
    try:
        async with motor.connect() as conexion:
            return await conexion.run_sync(operacion)
    finally:
        await motor.dispose()


def _revision_actual(conexion: Connection) -> str | None:
    return MigrationContext.configure(conexion).get_current_revision()


def _diferencias(conexion: Connection) -> list[str]:
    contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
    return [str(diferencia) for diferencia in compare_metadata(contexto, Base.metadata)]


def _pendientes(script: ScriptDirectory, actual: str | None) -> list[str]:
    head = script.get_current_head()
    if actual == head:
        return []
    try:
        revisiones = list(script.iterate_revisions(head, actual or "base"))
    except Exception as error:
        # La base está en una revisión que este código no conoce (otra rama ya migró Neon).
        raise CommandError(f"Can't locate revision identified by '{actual}'") from error
    return [f"{r.revision}: {r.doc}" for r in reversed(revisiones)]


def estado_esquema(database_url: str | None = None, comparar_modelos: bool = True) -> ResultadoActualizacion:
    """Informa revisión actual, pendientes y diferencias con los modelos, sin modificar la base."""
    config = configuracion_alembic(database_url)
    url = config.attributes["database_url"]
    script = ScriptDirectory.from_config(config)
    actual = asyncio.run(_con_conexion(url, _revision_actual))
    diferencias = asyncio.run(_con_conexion(url, _diferencias)) if comparar_modelos and actual else []
    return ResultadoActualizacion(
        base=url_segura(url),
        revision_anterior=actual,
        revision_actual=actual,
        revision_head=script.get_current_head(),
        pendientes=_pendientes(script, actual),
        diferencias=diferencias,
    )


def actualizar_esquema(database_url: str | None = None) -> ResultadoActualizacion:
    """Aplica las migraciones pendientes (adoptando una base heredada) y devuelve el estado final.

    Es sincrónica porque `env.py` de Alembic crea su propio event loop: desde
    código async se invoca con `asyncio.to_thread`.
    """
    config = configuracion_alembic(database_url)
    url = config.attributes["database_url"]
    script = ScriptDirectory.from_config(config)
    anterior = asyncio.run(_con_conexion(url, _revision_actual))
    pendientes = _pendientes(script, anterior)
    command.upgrade(config, "head")
    actual = asyncio.run(_con_conexion(url, _revision_actual))
    return ResultadoActualizacion(
        base=url_segura(url),
        revision_anterior=anterior,
        revision_actual=actual,
        revision_head=script.get_current_head(),
        pendientes=pendientes,
        diferencias=asyncio.run(_con_conexion(url, _diferencias)),
    )


def actualizar_esquema_al_iniciar() -> None:
    """Variante del arranque de la API: informa en el log y nunca impide que la app levante."""
    try:
        resultado = actualizar_esquema()
    except CommandError as error:
        if "Can't locate revision" in str(error):
            logger.error(
                "La base de datos está en una revisión más nueva que este código. Actualizá tu rama "
                "(git pull) antes de trabajar contra la base compartida. Detalle: %s", error,
            )
        else:
            logger.error("No se pudo actualizar el esquema de la base de datos: %s", error)
        return
    except EsquemaNoAdoptableError as error:
        logger.error(str(error))
        return

    if resultado.pendientes:
        logger.info(
            "Esquema actualizado en %s: %s -> %s (%s)",
            resultado.base, resultado.revision_anterior or "vacía", resultado.revision_actual,
            "; ".join(resultado.pendientes),
        )
    else:
        logger.info("Esquema de %s al día (revisión %s).", resultado.base, resultado.revision_actual)
    if resultado.diferencias:
        logger.warning(
            "Los modelos tienen cambios sin migración (%d). Generá una con "
            "`alembic revision --autogenerate`: %s", len(resultado.diferencias), "; ".join(resultado.diferencias),
        )


async def _sembrar(database_url: str) -> None:
    from app.infrastructure.db.seed import ejecutar_semillas

    url = normalizar_url_base_datos(database_url)
    motor = create_async_engine(url, poolclass=NullPool, connect_args=obtener_connect_args(url))
    try:
        async with async_sessionmaker(bind=motor, class_=AsyncSession, expire_on_commit=False)() as sesion:
            await ejecutar_semillas(sesion)
    finally:
        await motor.dispose()


def _imprimir(resultado: ResultadoActualizacion, aplicado: bool) -> None:
    print(f"Base: {resultado.base}")
    print(f"Revisión del código (head): {resultado.revision_head}")
    if aplicado:
        print(f"Revisión anterior: {resultado.revision_anterior or 'base vacía o sin Alembic'}")
        print(f"Revisión actual:   {resultado.revision_actual}")
        if resultado.pendientes:
            print("Migraciones aplicadas:")
            for pendiente in resultado.pendientes:
                print(f"  - {pendiente}")
        else:
            print("No había migraciones pendientes.")
    else:
        print(f"Revisión actual:   {resultado.revision_actual or 'base vacía o sin Alembic'}")
        print("Pendientes:" if resultado.pendientes else "Sin migraciones pendientes.")
        for pendiente in resultado.pendientes:
            print(f"  - {pendiente}")
    if resultado.diferencias:
        print("ATENCIÓN: los modelos tienen cambios que ninguna migración aplica:")
        for diferencia in resultado.diferencias:
            print(f"  - {diferencia}")


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Actualiza o verifica el esquema de la base (SQLite o Neon).")
    parser.add_argument(
        "--database-url",
        help="Connection string a usar (se acepta tal como lo copia Neon). Por defecto, DATABASE_URL del .env.",
    )
    parser.add_argument("--verificar", action="store_true", help="Solo informa el estado, sin modificar la base.")
    parser.add_argument("--semillas", action="store_true", help="Después de migrar, carga roles, sucursales y datos base.")
    opciones = parser.parse_args(argumentos)

    try:
        if opciones.verificar:
            resultado = estado_esquema(opciones.database_url)
            _imprimir(resultado, aplicado=False)
            return 0 if resultado.al_dia else 1
        resultado = actualizar_esquema(opciones.database_url)
        _imprimir(resultado, aplicado=True)
        if opciones.semillas:
            asyncio.run(_sembrar(opciones.database_url or settings.DATABASE_URL))
            print("Datos base sembrados (roles, Superadmin, sucursales y preguntas frecuentes).")
        return 0 if resultado.al_dia else 1
    except (CommandError, EsquemaNoAdoptableError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
