import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import RolModel, UsuarioModel
from app.infrastructure.db.session import AsyncSessionLocal, crear_tablas

ROLES_BASE = [
    {"id": RolIdEnum.SUPERADMIN.value, "nombre": RolEnum.SUPERADMIN.value, "descripcion": "Administrador general del sistema"},
    {"id": RolIdEnum.ADMINISTRATIVO.value, "nombre": RolEnum.ADMINISTRATIVO.value, "descripcion": "Usuario administrativo operativo"},
    {"id": RolIdEnum.VENDEDOR.value, "nombre": RolEnum.VENDEDOR.value, "descripcion": "Personal de terminal / venta"},
    {"id": RolIdEnum.REPARTIDOR.value, "nombre": RolEnum.REPARTIDOR.value, "descripcion": "Personal de reparto"},
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


async def ejecutar_siembra() -> None:
    """Ejecuta la siembra completa de datos iniciales."""
    logger.info("Iniciando creación de tablas y siembra de datos...")
    await crear_tablas()
    async with AsyncSessionLocal() as db:
        await sembrar_roles(db)
        await sembrar_superadmin(db)
    logger.info("Siembra completada con éxito.")


if __name__ == "__main__":
    asyncio.run(ejecutar_siembra())

