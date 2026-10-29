from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.contracts.recorridos import ListarRecorridosResponse, RecorridoResponse
from app.contracts.reparto import (
    ContactoEntregaResponse,
    EventoEntregaResponse,
    RegistrarEntregaRequest,
    RegistrarLlegadaRequest,
    RegistrarVisitaFallidaRequest,
    UbicacionRequest,
    UbicacionResponse,
)


class IServicioReparto(Protocol):
    async def listar(self, usuario: Any, fecha: date | None, estado: str | None) -> ListarRecorridosResponse: ...

    async def obtener(self, id: UUID, usuario: Any) -> RecorridoResponse: ...

    async def iniciar(self, id: UUID, usuario: Any) -> RecorridoResponse: ...

    async def optimizar(self, id: UUID, usuario: Any, desde: tuple[float, float] | None) -> RecorridoResponse:
        """Mejor orden de lo que falta, desde la ubicación del repartidor."""
        ...

    async def actualizar_ubicacion(
        self, id: UUID, datos: UbicacionRequest, usuario: Any
    ) -> tuple[UbicacionResponse, list[UUID]]:
        """Guarda la posición y, en larga distancia, registra la llegada por proximidad (10 km)."""
        ...

    async def obtener_ubicacion(self, id: UUID, usuario: Any) -> UbicacionResponse: ...

    async def registrar_llegada(
        self, id: UUID, datos: RegistrarLlegadaRequest, usuario: Any
    ) -> tuple[RecorridoResponse, list[UUID]]:
        """Llegada a la próxima sucursal de un recorrido entre sucursales; devuelve los paquetes listos para retirar."""
        ...

    async def contacto(self, id: UUID, codigo: str, usuario: Any) -> ContactoEntregaResponse: ...

    async def registrar_entrega(
        self, id: UUID, codigo: str, datos: RegistrarEntregaRequest, usuario: Any
    ) -> EventoEntregaResponse: ...

    async def registrar_visita_fallida(
        self, id: UUID, codigo: str, datos: RegistrarVisitaFallidaRequest, usuario: Any
    ) -> EventoEntregaResponse: ...

    async def obtener_firma(self, id: UUID, evento_id: UUID, usuario: Any) -> bytes: ...
