import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.application.interfaces.repositorio_recepciones import IRepositorioRecepciones
from app.infrastructure.db.models import (
    EnvioModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
)


class RepositorioRecepciones(IRepositorioRecepciones):
    """Acceso a datos de la recepción de paquetes en terminal con SQLAlchemy (HU06)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_paquete_por_codigo(self, codigo: str) -> Optional[PaqueteModel]:
        """Resuelve el código escaneado a un paquete precargado.

        Acepta tanto el `numero_paquete` impreso en el código de barras como el
        `id` (UUID) del paquete. Precarga el envío con su sucursal de destino y
        la sucursal actual para que el servicio pueda armar la respuesta sin
        disparar lazy loads en un contexto async.
        """
        condiciones = [PaqueteModel.numero_paquete == codigo]

        try:
            condiciones.append(PaqueteModel.id == uuid.UUID(codigo))
        except ValueError:
            # El código es un número de paquete, no un UUID: se busca solo por número.
            pass

        stmt = (
            select(PaqueteModel)
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
            )
            .where(or_(*condiciones))
        )
        resultado = await self.db.execute(stmt)
        return resultado.unique().scalar_one_or_none()

    async def registrar_recepcion_paquete(
        self,
        paquete_id: uuid.UUID,
        nuevo_estado: str,
        sucursal_id: int,
        historial_estado: HistorialEstadoPaqueteModel,
    ) -> PaqueteModel:
        """Actualiza estado y ubicación del paquete y agrega la fila de auditoría.

        El estado denormalizado (`paquetes.estado` / `paquetes.sucursal_actual_id`)
        y la fila append-only de `historial_estados_paquete` se escriben en el
        mismo commit, para que la lectura pública de HU04 y el historial nunca
        queden desfasados.
        """
        stmt = (
            select(PaqueteModel)
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
            )
            .where(PaqueteModel.id == paquete_id)
        )
        resultado = await self.db.execute(stmt)
        paquete = resultado.unique().scalar_one()

        paquete.estado = nuevo_estado
        paquete.sucursal_actual_id = sucursal_id

        self.db.add(historial_estado)

        await self.db.commit()
        await self.db.refresh(paquete)
        await self.db.refresh(historial_estado)

        return paquete
