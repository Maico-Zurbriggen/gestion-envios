from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.infrastructure.db.engine_utils import obtener_connect_args
from app.infrastructure.db.models import Base

# Configuración del motor asíncrono
engine_kwargs = {"echo": settings.DEBUG, "connect_args": obtener_connect_args(settings.DATABASE_URL)}

async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
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


async def crear_tablas() -> None:
    """Crea todas las tablas definidas en los modelos si no existen."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

