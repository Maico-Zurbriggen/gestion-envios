from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.infrastructure.db.engine_utils import normalizar_url_base_datos, obtener_connect_args

# Configuración del motor asíncrono
DATABASE_URL = normalizar_url_base_datos(settings.DATABASE_URL)
engine_kwargs = {"echo": settings.DEBUG, "connect_args": obtener_connect_args(DATABASE_URL)}

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def obtener_sesion_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesión de base de datos asíncrona para FastAPI Depends."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

