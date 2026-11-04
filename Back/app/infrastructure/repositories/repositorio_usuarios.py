from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import RolModel, UsuarioModel


class RepositorioUsuarios:
    """Implementación de acceso a datos para la entidad Usuario con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_por_id(self, id: UUID) -> UsuarioModel | None:
        """Siempre carga la relación `rol` (`selectinload`): casi todo flujo
        de autenticación necesita el nombre del rol para armar el JWT o
        validar permisos."""
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_dni(self, dni: str) -> UsuarioModel | None:
        """Usado tanto en el login (HU01/HU02) como en la validación de
        unicidad al dar de alta un empleado (HU01 Escenario 4)."""
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.dni == dni)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_email(self, email: str) -> UsuarioModel | None:
        """Validación de unicidad de email al dar de alta un empleado
        (HU01 Escenario 4)."""
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.email == email)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def crear(self, usuario: UsuarioModel) -> UsuarioModel:
        self.db.add(usuario)
        await self.db.commit()
        await self.db.refresh(usuario)
        # Recargar con relación rol
        return await self.obtener_por_id(usuario.id)  # type: ignore

    async def actualizar_password(self, id: UUID, nuevo_hash: str) -> bool:
        """Cambio obligatorio de contraseña (HU02): actualiza el hash y baja
        el flag `requiere_cambio_password` en la misma operación, para que
        ambos cambios queden atómicos."""
        stmt = (
            update(UsuarioModel)
            .where(UsuarioModel.id == id)
            .values(
                password_hash=nuevo_hash,
                requiere_cambio_password=False,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0


    async def listar(self, buscar: str | None = None, rol_id: int | None = None, estado: str | None = None) -> list[UsuarioModel]:
        """Usuarios del personal con su rol, ordenados por nombre. La búsqueda
        ignora mayúsculas y mira nombre, DNI, email y teléfono."""
        stmt = select(UsuarioModel).options(selectinload(UsuarioModel.rol)).order_by(func.lower(UsuarioModel.nombre))
        if buscar and buscar.strip():
            patron = f"%{buscar.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(UsuarioModel.nombre).like(patron),
                UsuarioModel.dni.like(patron),
                func.lower(UsuarioModel.email).like(patron),
                UsuarioModel.telefono.like(patron),
            ))
        if rol_id is not None:
            stmt = stmt.where(UsuarioModel.rol_id == rol_id)
        if estado:
            stmt = stmt.where(UsuarioModel.estado == estado)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def contar_superadmins_activos(self, excluir_id: UUID | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(UsuarioModel)
            .join(RolModel, RolModel.id == UsuarioModel.rol_id)
            .where(RolModel.nombre == "SUPERADMIN", UsuarioModel.estado == "Activo")
        )
        if excluir_id is not None:
            stmt = stmt.where(UsuarioModel.id != excluir_id)
        return int((await self.db.execute(stmt)).scalar_one())

    async def guardar(self, usuario: UsuarioModel) -> UsuarioModel:
        """Persiste los cambios de un usuario ya cargado y lo devuelve con su rol."""
        usuario_id = usuario.id
        await self.db.commit()
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.id == usuario_id)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def restablecer_password(self, id: UUID, nuevo_hash: str) -> bool:
        """Blanqueo por el Superadministrador: nueva clave temporal y cambio
        obligatorio en el próximo ingreso (mismo flujo que el alta, HU02)."""
        stmt = (
            update(UsuarioModel)
            .where(UsuarioModel.id == id)
            .values(password_hash=nuevo_hash, requiere_cambio_password=True)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
