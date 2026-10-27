def obtener_connect_args(database_url: str) -> dict:
    """Argumentos de conexión específicos por motor, compartidos entre la
    app (`session.py`) y Alembic (`migrations/env.py`), que arman sus
    engines por separado.

    - SQLite: `check_same_thread=False` para compartir la conexión entre
      threads (necesario con el pool por defecto de `aiosqlite`).
    - PostgreSQL (Neon): `ssl="require"` porque `asyncpg` no entiende el
      parámetro `sslmode` de la URL (es sintaxis de `psycopg2`); y
      `statement_cache_size=0` porque el pooler de Neon (PgBouncer en modo
      `transaction`) no es compatible con el cacheo de prepared statements
      de `asyncpg` — sin esto, una conexión pooled puede fallar con errores
      del estilo "prepared statement already exists" al reutilizar un
      backend distinto entre queries.
    """
    if "sqlite" in database_url:
        return {"check_same_thread": False}
    if "postgresql" in database_url:
        return {"ssl": "require", "statement_cache_size": 0}
    return {}


PARAMETROS_URL_NO_SOPORTADOS_ASYNCPG = {"sslmode", "channel_binding"}
"""Parámetros que Neon incluye en el connection string y `asyncpg` rechaza; el SSL ya lo fuerza `obtener_connect_args`."""


def normalizar_url_base_datos(database_url: str) -> str:
    """Acepta el connection string tal como lo copia el panel de Neon.

    `postgresql://` o `postgres://` pasan a `postgresql+asyncpg://` y se quitan
    `sslmode`/`channel_binding`. Las URLs ya preparadas y las de SQLite no cambian.
    """
    url = database_url.strip()
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            url = "postgresql+asyncpg://" + url[len(prefijo) :]
            break
    if not url.startswith("postgresql+asyncpg://") or "?" not in url:
        return url
    base, consulta = url.split("?", 1)
    parametros = [
        parametro
        for parametro in consulta.split("&")
        if parametro and parametro.split("=", 1)[0].lower() not in PARAMETROS_URL_NO_SOPORTADOS_ASYNCPG
    ]
    return f"{base}?{'&'.join(parametros)}" if parametros else base


def url_para_migraciones(database_url: str, database_url_migraciones: str | None = None) -> str:
    """URL con la que Alembic aplica el esquema.

    Neon recomienda el endpoint directo para DDL: el pooler (PgBouncer en modo
    `transaction`) no garantiza una sesión estable durante la migración. Si no
    se configuró una URL explícita, se deriva quitando `-pooler` del host.
    """
    if database_url_migraciones and database_url_migraciones.strip():
        return normalizar_url_base_datos(database_url_migraciones)
    url = normalizar_url_base_datos(database_url)
    if url.startswith("postgresql+asyncpg://") and "-pooler." in url and ".neon.tech" in url:
        return url.replace("-pooler.", ".", 1)
    return url
