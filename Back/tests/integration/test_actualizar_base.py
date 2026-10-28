"""El esquema de cualquier base (SQLite local o Neon) se actualiza solo con migraciones de Alembic."""

import asyncio
import logging
import sqlite3

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.infrastructure.db import actualizar_base
from app.infrastructure.db.actualizar_base import (
    EsquemaNoAdoptableError,
    actualizar_esquema,
    actualizar_esquema_al_iniciar,
    configuracion_alembic,
    estado_esquema,
)
from app.infrastructure.db.models import Base


@pytest.fixture
def base_sqlite(tmp_path, monkeypatch):
    ruta = tmp_path / "esquema.db"
    url = f"sqlite+aiosqlite:///{ruta.as_posix()}"
    # Nunca tocar la base real del desarrollador aunque su .env apunte a Neon.
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    monkeypatch.setattr(settings, "DATABASE_URL_MIGRACIONES", "")
    return ruta, url


def _columnas(ruta, tabla: str) -> set[str]:
    with sqlite3.connect(ruta) as db:
        return {fila[1] for fila in db.execute(f"PRAGMA table_info({tabla})")}


def _version(ruta) -> str:
    with sqlite3.connect(ruta) as db:
        return db.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def test_los_modelos_no_tienen_cambios_sin_migracion(base_sqlite):
    """Si esta prueba falla, se cambió `models.py` sin crear la migración: Neon quedaría desactualizada.
    Generarla con `alembic revision --autogenerate -m "..."` y revisarla antes de subirla."""
    _, url = base_sqlite
    resultado = actualizar_esquema(url)
    assert resultado.al_dia
    assert resultado.diferencias == [], "\n".join(resultado.diferencias)


def test_base_vacia_se_crea_completa_con_alembic(base_sqlite):
    ruta, url = base_sqlite
    resultado = actualizar_esquema(url)
    assert resultado.revision_anterior is None
    assert len(resultado.pendientes) >= 5
    assert _version(ruta) == resultado.revision_head
    # Repetirlo no hace nada.
    assert actualizar_esquema(url).pendientes == []


def test_adopta_una_base_creada_con_create_all(base_sqlite):
    """El caso que dejaba a Neon trabada: tablas creadas por la API sin `alembic_version`."""
    ruta, url = base_sqlite

    async def crear_con_create_all():
        motor = create_async_engine(url)
        async with motor.begin() as conexion:
            await conexion.run_sync(Base.metadata.create_all)
        await motor.dispose()

    asyncio.run(crear_con_create_all())
    resultado = actualizar_esquema(url)
    assert resultado.al_dia and resultado.diferencias == []
    assert _version(ruta) == resultado.revision_head


def test_adopta_una_base_heredada_vieja_y_le_agrega_las_columnas_nuevas(base_sqlite):
    ruta, url = base_sqlite
    config = configuracion_alembic(url)
    config.attributes["adoptar_base_existente"] = False
    command.upgrade(config, actualizar_base.REVISION_HU10)
    with sqlite3.connect(ruta) as db:
        db.execute("DROP TABLE alembic_version")  # como si la hubiera creado `create_all` en ese momento
    assert "procesando_at" not in _columnas(ruta, "notificaciones_envio")

    resultado = actualizar_esquema(url)
    assert resultado.revision_anterior is None and resultado.al_dia
    assert {"procesando_at", "evento_entrega_id"} <= _columnas(ruta, "notificaciones_envio")
    assert "receptor_fecha_nacimiento" in _columnas(ruta, "eventos_entrega")


def test_base_heredada_incompleta_no_se_adopta_a_ciegas(base_sqlite):
    ruta, url = base_sqlite
    with sqlite3.connect(ruta) as db:
        db.execute("CREATE TABLE usuarios (id TEXT PRIMARY KEY)")
    with pytest.raises(EsquemaNoAdoptableError):
        actualizar_esquema(url)


def test_estado_informa_pendientes_sin_modificar(base_sqlite):
    ruta, url = base_sqlite
    config = configuracion_alembic(url)
    command.upgrade(config, actualizar_base.REVISION_INICIAL)
    estado = estado_esquema(url, comparar_modelos=False)
    assert not estado.al_dia and len(estado.pendientes) == 5
    assert _version(ruta) == actualizar_base.REVISION_INICIAL


def test_cli_verificar_y_actualizar(base_sqlite, capsys):
    _, url = base_sqlite
    assert actualizar_base.main(["--database-url", url, "--verificar"]) == 1
    assert actualizar_base.main(["--database-url", url]) == 0
    assert actualizar_base.main(["--database-url", url, "--verificar"]) == 0
    assert "Sin migraciones pendientes" in capsys.readouterr().out


def test_al_iniciar_una_base_mas_nueva_que_el_codigo_no_tumba_la_api(base_sqlite, caplog):
    ruta, url = base_sqlite
    actualizar_esquema(url)
    with sqlite3.connect(ruta) as db:
        db.execute("UPDATE alembic_version SET version_num = 'revisionfutura'")
    with caplog.at_level(logging.ERROR):
        actualizar_esquema_al_iniciar()
    assert "git pull" in caplog.text
