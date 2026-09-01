import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import RolModel, SucursalModel, UsuarioModel
from app.infrastructure.db.session import AsyncSessionLocal, crear_tablas

ROLES_BASE = [
    {"id": RolIdEnum.SUPERADMIN.value, "nombre": RolEnum.SUPERADMIN.value, "descripcion": "Administrador general del sistema"},
    {"id": RolIdEnum.ADMINISTRATIVO.value, "nombre": RolEnum.ADMINISTRATIVO.value, "descripcion": "Usuario administrativo operativo"},
    {"id": RolIdEnum.VENDEDOR.value, "nombre": RolEnum.VENDEDOR.value, "descripcion": "Personal de terminal / venta"},
    {"id": RolIdEnum.REPARTIDOR.value, "nombre": RolEnum.REPARTIDOR.value, "descripcion": "Personal de reparto"},
]

SUCURSALES_BASE = [
    {"nombre": "Sucursal Córdoba Centro", "provincia": "Córdoba", "ciudad": "Córdoba", "direccion": "Av. Colón 1234", "latitud": -31.4167, "longitud": -64.1833},
    {"nombre": "Sucursal Rosario Sur", "provincia": "Santa Fe", "ciudad": "Rosario", "direccion": "Bv. Oroño 2456", "latitud": -32.9587, "longitud": -60.6931},
    {"nombre": "Sucursal Mendoza Capital", "provincia": "Mendoza", "ciudad": "Mendoza", "direccion": "San Martín 890", "latitud": -32.8908, "longitud": -68.8272},
    {"nombre": "Sucursal Buenos Aires Palermo", "provincia": "Buenos Aires", "ciudad": "CABA", "direccion": "Av. Santa Fe 3450", "latitud": -34.5875, "longitud": -58.4205},
    {"nombre": "Sucursal Salta Norte", "provincia": "Salta", "ciudad": "Salta", "direccion": "Av. Sarmiento 555", "latitud": -24.7859, "longitud": -65.4117},
    {"nombre": "Sucursal Mar del Plata", "provincia": "Buenos Aires", "ciudad": "Mar del Plata", "direccion": "Av. Colón 3020", "latitud": -38.0055, "longitud": -57.5426},
]


async def sembrar_roles(db: AsyncSession) -> None:
    """Inserta los roles predeterminados si no existen."""
    for rol_data in ROLES_BASE:
        stmt = select(RolModel).where(RolModel.id == rol_data["id"])
        result = await db.execute(stmt)
        existente = result.scalar_one_or_none()
        if not existente:
            rol = RolModel(
                id=rol_data["id"],
                nombre=rol_data["nombre"],
                descripcion=rol_data["descripcion"],
            )
            db.add(rol)
            logger.info(f"Sembrando rol: {rol_data['nombre']}")
    await db.commit()


async def sembrar_superadmin(db: AsyncSession) -> None:
    """Inserta el usuario Superadministrador inicial desde variables de entorno."""
    password_plana = settings.SUPERADMIN_SEED_PASSWORD
    if not password_plana:
        logger.warning("No se definió SUPERADMIN_SEED_PASSWORD. Omitiendo seed de Superadmin.")
        return

    dni = settings.SUPERADMIN_SEED_DNI
    email = settings.SUPERADMIN_SEED_EMAIL

    stmt = select(UsuarioModel).where((UsuarioModel.dni == dni) | (UsuarioModel.email == email))
    result = await db.execute(stmt)
    existente = result.scalar_one_or_none()

    if not existente:
        password_hash = HasherContrasenas.generar_hash(password_plana)
        superadmin = UsuarioModel(
            nombre=settings.SUPERADMIN_SEED_NOMBRE,
            dni=dni,
            email=email,
            telefono=settings.SUPERADMIN_SEED_TELEFONO,
            password_hash=password_hash,
            estado="Activo",
            requiere_cambio_password=False,
            rol_id=RolIdEnum.SUPERADMIN.value,
        )
        db.add(superadmin)
        await db.commit()
        logger.info(f"Superadministrador sembrado exitosamente: {email} (DNI: {dni})")
    else:
        logger.info(f"Superadministrador ya existente ({email} / {dni}).")


async def sembrar_sucursales(db: AsyncSession) -> None:
    """Inserta las sucursales predeterminadas si no existen (matching por nombre)."""
    for datos in SUCURSALES_BASE:
        stmt = select(SucursalModel).where(SucursalModel.nombre == datos["nombre"])
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            db.add(SucursalModel(**datos))
            logger.info(f"Sembrando sucursal: {datos['nombre']}")
    await db.commit()


async def ejecutar_siembra() -> None:
    """Ejecuta la siembra completa de datos iniciales."""
    logger.info("Iniciando creación de tablas y siembra de datos...")
    await crear_tablas()
    async with AsyncSessionLocal() as db:
        await sembrar_roles(db)
        await sembrar_superadmin(db)
        await sembrar_sucursales(db)
    logger.info("Siembra completada con éxito.")


if __name__ == "__main__":
    asyncio.run(ejecutar_siembra())

