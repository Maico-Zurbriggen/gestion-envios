from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.contracts.recorridos import (
    AlertaRecorridoResponse,
    CompletarUbicacionPaqueteRequest,
    EliminarRecorridoResponse,
    GenerarRecorridosRequest,
    GenerarRecorridosResponse,
    ListarAlertasRecorridoResponse,
    ListarRecorridosResponse,
    ReasignarRepartidorRequest,
    RecorridoResponse,
    ReemplazarPaquetesRecorridoRequest,
)


class IServicioRecorridos(Protocol):
    """Protocolo del servicio de recorridos de reparto (HU10)."""

    async def generar(self, datos: GenerarRecorridosRequest, usuario: Any) -> GenerarRecorridosResponse:
        """Generación automática (Escenario 1) con alertas de lo que quedó afuera (Escenario 3)."""
        ...

    async def listar(
        self,
        sucursal_id: int | None = None,
        fecha: date | None = None,
        tipo_distancia: str | None = None,
        estado: str | None = None,
        repartidor_id: UUID | None = None,
    ) -> ListarRecorridosResponse: ...

    async def obtener(self, id: UUID) -> RecorridoResponse:
        """Visualización del recorrido (Escenario 2)."""
        ...

    async def reemplazar_paquetes(self, id: UUID, datos: ReemplazarPaquetesRecorridoRequest) -> RecorridoResponse:
        """Edición manual de composición y orden (Escenario 2)."""
        ...

    async def quitar_paquete(self, id: UUID, codigo: str) -> RecorridoResponse: ...

    async def paradas_en_sucursales(self, recorrido: Any) -> list[tuple[Any, list[Any]]]:
        """Paradas en sucursales de un recorrido ya cargado, en orden, con sus paquetes."""
        ...

    async def paquetes_que_bajan_en(self, recorridos: list[Any], sucursal_id: int) -> dict[UUID, list[Any]]:
        """Por recorrido ya cargado, los paquetes cuya parada es esa sucursal (misma regla que el detalle)."""
        ...

    async def completar_ubicacion(
        self, id: UUID, codigo: str, datos: CompletarUbicacionPaqueteRequest
    ) -> RecorridoResponse: ...

    async def optimizar(self, id: UUID) -> RecorridoResponse:
        """Vuelve a calcular el mejor orden de visita de los paquetes actuales."""
        ...

    async def reasignar_repartidor(self, id: UUID, datos: ReasignarRepartidorRequest) -> RecorridoResponse: ...

    async def iniciar(self, id: UUID, usuario: Any) -> RecorridoResponse:
        """Despacha el recorrido: los paquetes salen de la sucursal."""
        ...

    async def eliminar(self, id: UUID) -> EliminarRecorridoResponse: ...

    async def listar_alertas(
        self,
        sucursal_id: int | None = None,
        incluir_resueltas: bool = False,
    ) -> ListarAlertasRecorridoResponse: ...

    async def resolver_alerta(self, id: UUID) -> AlertaRecorridoResponse: ...
