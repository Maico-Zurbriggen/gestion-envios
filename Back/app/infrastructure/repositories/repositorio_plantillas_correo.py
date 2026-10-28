from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import ConfiguracionCorreoModel, PlantillaCorreoModel

ID_CONFIGURACION = 1


class RepositorioPlantillasCorreo:
    """Textos editados de los correos y datos de la empresa que los firma."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_plantillas(self) -> dict[str, PlantillaCorreoModel]:
        result = await self.db.execute(select(PlantillaCorreoModel))
        return {fila.clave: fila for fila in result.scalars().all()}

    async def obtener_configuracion(self) -> ConfiguracionCorreoModel | None:
        return await self.db.get(ConfiguracionCorreoModel, ID_CONFIGURACION)

    async def guardar_plantilla(self, clave: str, campos: dict[str, str | None], usuario_id: UUID | None) -> PlantillaCorreoModel:
        fila = await self.db.get(PlantillaCorreoModel, clave)
        if fila is None:
            fila = PlantillaCorreoModel(clave=clave)
            self.db.add(fila)
        for campo, valor in campos.items():
            setattr(fila, campo, valor)
        fila.actualizado_por_id = usuario_id
        await self.db.commit()
        await self.db.refresh(fila)
        return fila

    async def eliminar_plantilla(self, clave: str) -> None:
        await self.db.execute(delete(PlantillaCorreoModel).where(PlantillaCorreoModel.clave == clave))
        await self.db.commit()

    async def guardar_configuracion(self, campos: dict[str, str | None], usuario_id: UUID | None) -> ConfiguracionCorreoModel:
        fila = await self.db.get(ConfiguracionCorreoModel, ID_CONFIGURACION)
        if fila is None:
            fila = ConfiguracionCorreoModel(id=ID_CONFIGURACION)
            self.db.add(fila)
        for campo, valor in campos.items():
            setattr(fila, campo, valor)
        fila.actualizado_por_id = usuario_id
        await self.db.commit()
        await self.db.refresh(fila)
        return fila
