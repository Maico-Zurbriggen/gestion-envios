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