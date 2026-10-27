import uuid

from sqlalchemy import or_, select, update
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

    async def obtener_por_operacion(self, operacion_id: uuid.UUID) -> EventoEntregaModel | None:
        resultado = await self.db.execute(
            select(EventoEntregaModel).where(EventoEntregaModel.operacion_id == operacion_id)
        )
        return resultado.scalar_one_or_none()

    async def obtener_evento(self, evento_id: uuid.UUID) -> EventoEntregaModel | None:
        return await self.db.get(EventoEntregaModel, evento_id)

    async def buscar_paquete_por_id_o_codigo(self, id_o_codigo: str) -> PaqueteModel | None:
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
        sucursal_actual_id: int | None = None,
        estados_previos: set[str] | None = None,
    ) -> PaqueteModel | None:
        """Transición condicional del paquete + evento + historial en un único commit.

        El `UPDATE ... WHERE estado IN (...)` es la barrera contra retiros
        simultáneos: solo una solicitud cambia la fila. Si otra ya lo hizo,
        no se escribe nada y se devuelve `None`.
        """
        valores: dict = {"estado": nuevo_estado}
        if sucursal_actual_id is not None:
            valores["sucursal_actual_id"] = sucursal_actual_id
        condiciones = [PaqueteModel.id == paquete_id]
        if estados_previos:
            condiciones.append(PaqueteModel.estado.in_(list(estados_previos)))
        resultado = await self.db.execute(
            update(PaqueteModel).where(*condiciones).values(**valores).execution_options(synchronize_session=False)
        )
        if resultado.rowcount != 1:
            await self.db.rollback()
            return None

        self.db.add(evento_entrega)
        self.db.add(historial_estado)
        await self.db.commit()

        stmt = (
            select(PaqueteModel)
            .options(
                joinedload(PaqueteModel.envio).joinedload(EnvioModel.sucursal_destino),
                joinedload(PaqueteModel.sucursal_actual),
            )
            .where(PaqueteModel.id == paquete_id)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).unique().scalar_one()
