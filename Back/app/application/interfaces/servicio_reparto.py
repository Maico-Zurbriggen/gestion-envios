from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.contracts.recorridos import ListarRecorridosResponse, RecorridoResponse
from app.contracts.reparto import (
    ContactoEntregaResponse,
    EventoEntregaResponse,
    RegistrarEntregaRequest,
    RegistrarVisitaFallidaRequest,
    UbicacionRequest,
    UbicacionResponse,
)


class IServicioReparto(Protocol):
    async def listar(self, usuario: Any, fecha: date | None, estado: str | None) -> ListarRecorridosResponse: ...

    async def obtener(self, id: UUID, usuario: Any) -> RecorridoResponse: ...

    async def iniciar(self, id: UUID, usuario: Any) -> RecorridoResponse: ...

    async def actualizar_ubicacion(self, id: UUID, datos: UbicacionRequest, usuario: Any) -> UbicacionResponse: ...

    async def obtener_ubicacion(self, id: UUID, usuario: Any) -> UbicacionResponse: ...

    async def contacto(self, id: UUID, codigo: str, usuario: Any) -> ContactoEntregaResponse: ...

    async def registrar_entrega(
        self, id: UUID, codigo: str, datos: RegistrarEntregaRequest, usuario: Any
    ) -> EventoEntregaResponse: ...

    async def registrar_visita_fallida(
        self, id: UUID, codigo: str, datos: RegistrarVisitaFallidaRequest, usuario: Any
    ) -> EventoEntregaResponse: ...

    async def obtener_firma(self, id: UUID, evento_id: UUID, usuario: Any) -> bytes: ...
