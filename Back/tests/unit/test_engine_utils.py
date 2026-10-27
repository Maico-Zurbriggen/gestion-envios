from app.infrastructure.db.engine_utils import normalizar_url_base_datos, url_para_migraciones

NEON = "postgresql://user:clave@ep-cool-123-pooler.sa-east-1.aws.neon.tech/gestion?sslmode=require&channel_binding=require"


def test_acepta_el_connection_string_tal_como_lo_copia_neon():
    assert normalizar_url_base_datos(NEON) == (
        "postgresql+asyncpg://user:clave@ep-cool-123-pooler.sa-east-1.aws.neon.tech/gestion"
    )
    assert normalizar_url_base_datos("postgres://u:p@h/db?sslmode=require&application_name=api") == (
        "postgresql+asyncpg://u:p@h/db?application_name=api"
    )


def test_urls_ya_preparadas_y_sqlite_no_cambian():
    assert normalizar_url_base_datos("sqlite+aiosqlite:///./gestion_envios.db") == "sqlite+aiosqlite:///./gestion_envios.db"
    assert normalizar_url_base_datos("postgresql+asyncpg://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"


def test_las_migraciones_usan_el_endpoint_directo_de_neon():
    assert url_para_migraciones(NEON) == "postgresql+asyncpg://user:clave@ep-cool-123.sa-east-1.aws.neon.tech/gestion"
    assert url_para_migraciones(NEON, "postgresql://otra/db") == "postgresql+asyncpg://otra/db"
    assert url_para_migraciones("sqlite+aiosqlite:///x.db") == "sqlite+aiosqlite:///x.db"
