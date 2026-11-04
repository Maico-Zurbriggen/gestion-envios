import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.infrastructure.db.engine_utils import obtener_connect_args, url_para_migraciones
from app.infrastructure.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# `actualizar_base.py` pasa la URL ya resuelta; el CLI de Alembic usa la del .env
# (con el endpoint directo de Neon si DATABASE_URL apunta al pooler).
DATABASE_URL = config.attributes.get("database_url") or url_para_migraciones(
    settings.DATABASE_URL, settings.DATABASE_URL_MIGRACIONES
)
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

LLAVE_CANDADO_MIGRACIONES = 2026_0501
"""Candado asesor de PostgreSQL: serializa migraciones simultáneas contra la base compartida."""


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        if connection.dialect.name == "postgresql":
            # Se libera solo al terminar la transacción: quien llegue segundo espera y ve la base ya migrada.
            connection.execute(text("SELECT pg_advisory_xact_lock(:llave)"), {"llave": LLAVE_CANDADO_MIGRACIONES})
        if config.attributes.get("adoptar_base_existente"):
            from app.infrastructure.db.actualizar_base import retirar_alcance_quitado, revision_de_base_heredada

            if retirar_alcance_quitado(connection) and connection.in_transaction():
                # Las tablas y revisiones retiradas se limpian antes de migrar (también en SQLite).
                connection.commit()
            revision = revision_de_base_heredada(connection)
            if revision:
                # Base creada con `create_all`: se marca en su revisión real y se migra desde ahí.
                migracion = context.get_context()
                migracion.stamp(context.script, revision)
                if not migracion.impl.transactional_ddl and connection.in_transaction():
                    # SQLite: sin DDL transaccional la marca quedaría en una transacción
                    # implícita que nadie confirma si no hay migraciones posteriores.
                    connection.commit()
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine and associate a connection with the context."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=obtener_connect_args(DATABASE_URL),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

