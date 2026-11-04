from datetime import datetime
from typing import Any, Protocol


class IRepositorioPlazos(Protocol):
    """Paquetes cuyo plazo venció: registros sin admitir y retiros no realizados."""

    async def pre_registros_anteriores_a(self, limite: datetime) -> list[Any]: ...

    async def retiros_vencidos(self, ahora: datetime) -> list[Any]: ...

    async def agregar(self, entidad: Any) -> None: ...

    async def confirmar(self) -> None: ...
