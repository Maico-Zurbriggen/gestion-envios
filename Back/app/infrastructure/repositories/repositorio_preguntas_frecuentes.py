from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositorio_preguntas_frecuentes import IRepositorioPreguntasFrecuentes
from app.infrastructure.db.models import PreguntaFrecuenteModel


class RepositorioPreguntasFrecuentes(IRepositorioPreguntasFrecuentes):
    """Acceso a datos de las preguntas frecuentes con SQLAlchemy (HU08)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar(self, solo_publicadas: bool = True) -> list[PreguntaFrecuenteModel]:
        """El orden lo decide únicamente `orden` (y el `id` como desempate), no
        la categoría: así quien administra el contenido controla también en qué
        orden aparecen las secciones (la de su primera pregunta)."""
        stmt = select(PreguntaFrecuenteModel)
        if solo_publicadas:
            stmt = stmt.where(PreguntaFrecuenteModel.publicada.is_(True))
        stmt = stmt.order_by(PreguntaFrecuenteModel.orden, PreguntaFrecuenteModel.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def obtener_por_id(self, id: int) -> PreguntaFrecuenteModel | None:
        stmt = select(PreguntaFrecuenteModel).where(PreguntaFrecuenteModel.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def crear(self, pregunta: PreguntaFrecuenteModel) -> PreguntaFrecuenteModel:
        self.db.add(pregunta)
        await self.db.commit()
        await self.db.refresh(pregunta)
        return pregunta

    async def actualizar(self, pregunta: PreguntaFrecuenteModel) -> PreguntaFrecuenteModel:
        await self.db.commit()
        await self.db.refresh(pregunta)
        return pregunta

    async def eliminar(self, pregunta: PreguntaFrecuenteModel) -> None:
        await self.db.delete(pregunta)
        await self.db.commit()
