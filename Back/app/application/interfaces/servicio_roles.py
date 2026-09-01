from typing import Protocol

from app.contracts.roles import ListaRolesResponse


class IServicioRoles(Protocol):
    """Protocolo del servicio para consulta de roles del sistema."""

    async def listar_roles(self) -> ListaRolesResponse: ...

