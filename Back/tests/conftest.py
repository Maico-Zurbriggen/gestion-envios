import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session_factory, obtener_sesion_db
from app.api.main import app
from app.core.config import settings
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import Base, RolModel, SucursalModel, UsuarioModel

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Crea una base de datos limpia en memoria para cada test y siembra roles y superadmin."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Sembrar roles
        roles = [
            RolModel(id=RolIdEnum.SUPERADMIN.value, nombre=RolEnum.SUPERADMIN.value, descripcion="Superadmin"),
            RolModel(id=RolIdEnum.ADMINISTRATIVO.value, nombre=RolEnum.ADMINISTRATIVO.value, descripcion="Administrativo"),
            RolModel(id=RolIdEnum.VENDEDOR.value, nombre=RolEnum.VENDEDOR.value, descripcion="Vendedor"),
            RolModel(id=RolIdEnum.REPARTIDOR.value, nombre=RolEnum.REPARTIDOR.value, descripcion="Repartidor"),
        ]
        session.add_all(roles)
        await session.commit()

        # Sembrar Superadmin
        superadmin = UsuarioModel(
            nombre=settings.SUPERADMIN_SEED_NOMBRE,
            dni=settings.SUPERADMIN_SEED_DNI,
            email=settings.SUPERADMIN_SEED_EMAIL,
            telefono=settings.SUPERADMIN_SEED_TELEFONO,
            password_hash=HasherContrasenas.generar_hash(settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*"),
            estado="Activo",
            requiere_cambio_password=False,
            rol_id=RolIdEnum.SUPERADMIN.value,
        )
        session.add(superadmin)
        await session.commit()
        await session.refresh(superadmin)

        # Sembrar Sucursales (mínimo set para tests de HU03/HU04)
        sucursales = [
            SucursalModel(
                id=1,
                nombre="Sucursal Test Centro",
                provincia="Córdoba",
                ciudad="Córdoba",
                direccion="Calle Falsa 123",
                latitud=-31.4,
                longitud=-64.18,
            ),
            SucursalModel(
                id=2,
                nombre="Sucursal Test Norte",
                provincia="Santa Fe",
                ciudad="Rosario",
                direccion="Bv. Test 456",
                latitud=-32.95,
                longitud=-60.69,
            ),
        ]
        session.add_all(sucursales)
        await session.commit()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP de prueba asíncrono configurado con la DB en memoria."""
    async def override_obtener_sesion_db():
        yield db_session

    app.dependency_overrides[obtener_sesion_db] = override_obtener_sesion_db
    app.dependency_overrides[get_session_factory] = lambda: TestingSessionLocal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def superadmin_token(db_session: AsyncSession) -> str:
    """Genera un token JWT de superadmin con FULL_ACCESS."""
    return ManejadorJWT.emitir_token(
        usuario_id="00000000-0000-0000-0000-000000000001",
        rol=RolEnum.SUPERADMIN.value,
        scope=ScopeEnum.FULL_ACCESS.value,
    )


@pytest_asyncio.fixture
async def administrativo_usuario(db_session: AsyncSession) -> UsuarioModel:
    """Crea y persiste un usuario con rol ADMINISTRATIVO para pruebas de sucursal."""
    admin = UsuarioModel(
        nombre="Laura Martínez",
        dni="35999888",
        email="laura.admin@empresa.com",
        telefono="+543564999888",
        password_hash=HasherContrasenas.generar_hash("AdminPass123!*"),
        estado="Activo",
        requiere_cambio_password=False,
        rol_id=RolIdEnum.ADMINISTRATIVO.value,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def administrativo_token(administrativo_usuario: UsuarioModel) -> str:
    """Genera un token JWT con rol ADMINISTRATIVO y FULL_ACCESS."""
    return ManejadorJWT.emitir_token(
        usuario_id=str(administrativo_usuario.id),
        rol=RolEnum.ADMINISTRATIVO.value,
        scope=ScopeEnum.FULL_ACCESS.value,
    )


@pytest_asyncio.fixture
async def vendedor_usuario(db_session: AsyncSession) -> UsuarioModel:
    """Crea y persiste un usuario con rol VENDEDOR para pruebas de autorización."""
    vendedor = UsuarioModel(
        nombre="Marcos Vendedor",
        dni="36111222",
        email="marcos.vendedor@empresa.com",
        telefono="+543564111333",
        password_hash=HasherContrasenas.generar_hash("VendedorPass123!*"),
        estado="Activo",
        requiere_cambio_password=False,
        rol_id=RolIdEnum.VENDEDOR.value,
    )
    db_session.add(vendedor)
    await db_session.commit()
    await db_session.refresh(vendedor)
    return vendedor


@pytest_asyncio.fixture
async def vendedor_token(vendedor_usuario: UsuarioModel) -> str:
    """Genera un token JWT con rol VENDEDOR y FULL_ACCESS para probar autorización."""
    return ManejadorJWT.emitir_token(
        usuario_id=str(vendedor_usuario.id),
        rol=RolEnum.VENDEDOR.value,
        scope=ScopeEnum.FULL_ACCESS.value,
    )

