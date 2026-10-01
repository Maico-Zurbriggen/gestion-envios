from typing import Optional
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.application.interfaces.repositorio_entregas import IRepositorioEntregas
from app.infrastructure.db.models import (
    EnvioModel,
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
)


class RepositorioEntregas(IRepositorioEntregas):
    """Implementación de acceso a datos para eventos de retiro y entrega con SQLAlchemy (HU13)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_paquete_por_id_o_codigo(self, id_o_codigo: str) -> Optional[PaqueteModel]:
        """Busca un paquete por UUID o por numero_paquete (ej. PAQ-XXXXXXXXXX)."""
        codigo_limpio = id_o_codigo.strip()
        condiciones = [PaqueteModel.numero_paquete == codigo_limpio]

        try:
            val_uuid = uuid.UUID(codigo_limpio)
            condiciones.append(PaqueteModel.id == val_uuid)
        except ValueError:
            pass

        stmt = (
            select(PaqueteModel)
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
            )
            .where(or_(*condiciones))
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def registrar_retiro_paquete(
        self,
        paquete_id: uuid.UUID,
        nuevo_estado: str,
        evento_entrega: EventoEntregaModel,
        historial_estado: HistorialEstadoPaqueteModel,
        sucursal_actual_id: Optional[int] = None,
    ) -> PaqueteModel:
        """Actualiza el estado del paquete y almacena el evento e historial transaccionalmente."""
        stmt = (
            select(PaqueteModel)
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
            )
            .where(PaqueteModel.id == paquete_id)
        )
        result = await self.db.execute(stmt)
        paquete = result.unique().scalar_one()

        paquete.estado = nuevo_estado
        if sucursal_actual_id is not None:
            paquete.sucursal_actual_id = sucursal_actual_id

        self.db.add(evento_entrega)
        self.db.add(historial_estado)

        await self.db.commit()
        await self.db.refresh(paquete)
        await self.db.refresh(evento_entrega)
        await self.db.refresh(historial_estado)

        return paquete
