from contextlib import asynccontextmanager
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import registrar_manejadores_excepciones
from app.api.v1.routers.admin import router as admin_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.roles import router as roles_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.infrastructure.db.seed import ejecutar_siembra


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización de logs, DB y seed."""
    setup_logging()
    logger.info(f"Iniciando {settings.PROJECT_NAME}...")
    try:
        await ejecutar_siembra()
    except Exception as e:
        logger.error(f"Error durante la inicialización/siembra de BD: {e}", exc_info=True)
    yield
    logger.info(f"Deteniendo {settings.PROJECT_NAME}...")


def crear_aplicacion() -> FastAPI:
    """Fábrica para crear y configurar la aplicación FastAPI."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Backend API REST para el Sistema de Gestión de Envíos y Distribución (Sprint 1)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware de Correlation ID para trazabilidad
    app.add_middleware(CorrelationIdMiddleware)

    # Configuración de CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registro de manejadores de excepciones estándar
    registrar_manejadores_excepciones(app)

    # Montaje de routers con prefijo /api/v1
    app.include_router(health_router, prefix=settings.API_V1_STR)
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(admin_router, prefix=settings.API_V1_STR)
    app.include_router(roles_router, prefix=settings.API_V1_STR)

    # Health check también en la raíz
    app.include_router(health_router)


    return app


app = crear_aplicacion()

