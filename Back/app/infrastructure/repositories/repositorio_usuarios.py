from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import UsuarioModel


class RepositorioUsuarios:
    """Implementación de acceso a datos para la entidad Usuario con SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_por_id(self, id: UUID) -> Optional[UsuarioModel]:
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_dni(self, dni: str) -> Optional[UsuarioModel]:
        stmt = (
            select(UsuarioModel)
            .options(selectinload(UsuarioModel.rol))
            .where(UsuarioModel.dni == dni)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_email(self, email: str) -> Optional[UsuarioModel]:
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

