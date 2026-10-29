"""Plazos del circuito logístico.

- **Registro vencido:** un envío registrado online que no se llevó a una sucursal
  dentro del plazo se da de baja (VENCIDO) y se avisa al remitente.
- **Retiro vencido:** un paquete que nadie retiró a tiempo pasa a devolución. Si
  ya está en la sucursal de origen, queda para que lo retire el remitente; si no,
  espera un recorrido que lo lleve de vuelta (EN_DEVOLUCION).

Se ejecuta periódicamente y también se puede disparar a mano desde el monitor.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.application.interfaces.repositorio_plazos import IRepositorioPlazos
from app.contracts.monitor import PlazosProcesadosData, PlazosProcesadosResponse
from app.core.config import settings
from app.domain.constants.estados_logistica import EstadoPaqueteEnum, TipoAvisoEnum
from app.domain.rules.circuito_rules import retiro_vencido
from app.infrastructure.db.models import HistorialEstadoPaqueteModel


class ServicioPlazos:
    def __init__(self, repositorio: IRepositorioPlazos, notificaciones: Any | None = None):
        self.repo = repositorio
        self.notificaciones = notificaciones

    async def procesar(self, ahora: datetime | None = None) -> PlazosProcesadosResponse:
        ahora = ahora or datetime.now(UTC)
        avisos: list[tuple[Any, str]] = []

        vencidos = 0
        envios_avisados: set[Any] = set()
        limite = ahora - timedelta(days=settings.VENCIMIENTO_PRE_REGISTRO_DIAS)
        for paquete in await self.repo.pre_registros_anteriores_a(limite):
            anterior = paquete.estado
            paquete.estado = EstadoPaqueteEnum.VENCIDO.value
            await self.repo.agregar(HistorialEstadoPaqueteModel(
                paquete_id=paquete.id,
                estado_anterior=anterior,
                estado_nuevo=EstadoPaqueteEnum.VENCIDO.value,
                usuario_id=None,
                observacion=(
                    f"El registro venció: el paquete no llegó a una sucursal en "
                    f"{settings.VENCIMIENTO_PRE_REGISTRO_DIAS} días."
                ),
                created_at=ahora,
            ))
            vencidos += 1
            # Un solo aviso por envío, aunque tenga varios paquetes.
            if paquete.envio_id not in envios_avisados:
                envios_avisados.add(paquete.envio_id)
                avisos.append((paquete.id, TipoAvisoEnum.VENCIDO.value))

        devoluciones = 0
        for paquete in await self.repo.retiros_vencidos(ahora):
            if not retiro_vencido(paquete.estado, paquete.retiro_hasta, paquete.en_devolucion, ahora):
                continue
            anterior = paquete.estado
            origen = paquete.sucursal_origen_id or paquete.sucursal_actual_id
            ya_en_origen = origen == paquete.sucursal_actual_id
            paquete.en_devolucion = True
            paquete.sucursal_origen_id = origen
            paquete.retiro_hasta = None
            paquete.estado = (
                EstadoPaqueteEnum.LISTO_PARA_RETIRO.value if ya_en_origen else EstadoPaqueteEnum.EN_DEVOLUCION.value
            )
            await self.repo.agregar(HistorialEstadoPaqueteModel(
                paquete_id=paquete.id,
                estado_anterior=anterior,
                estado_nuevo=paquete.estado,
                usuario_id=None,
                sucursal_id=paquete.sucursal_actual_id,
                observacion=(
                    "No se retiró dentro del plazo: vuelve al remitente. "
                    + ("Ya está en la sucursal de origen para que lo retire." if ya_en_origen
                       else "Espera el recorrido de vuelta a la sucursal de origen.")
                ),
                created_at=ahora,
            ))
            devoluciones += 1
            # Si ya está en origen alcanza con un aviso: «ya podés retirar el paquete devuelto».
            avisos.append((paquete.id, TipoAvisoEnum.LISTO_PARA_RETIRO.value if ya_en_origen else TipoAvisoEnum.DEVOLUCION.value))

        await self.repo.confirmar()
        if self.notificaciones is not None:
            for paquete_id, tipo in avisos:
                await self.notificaciones.notificar_hito(paquete_id, tipo)
        return PlazosProcesadosResponse(data=PlazosProcesadosData(
            registros_vencidos=vencidos, devoluciones_iniciadas=devoluciones, procesado_at=ahora,
        ))
