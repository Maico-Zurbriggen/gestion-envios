from app.application.interfaces.repositorio_roles import IRepositorioRoles
from app.contracts.roles import ListaRolesResponse, RolResponse


class ServicioRoles:
    """Servicio que implementa la consulta de roles del sistema."""

    def __init__(self, repositorio_roles: IRepositorioRoles):
        self.repo_roles = repositorio_roles

    async def listar_roles(self) -> ListaRolesResponse:
        """Obtiene todos los roles registrados en el sistema con sus IDs numéricos."""
        roles_db = await self.repo_roles.obtener_todos()
        roles_dto = [
            RolResponse(
                id=rol.id,
                nombre=rol.nombre,
                descripcion=rol.descripcion,
            )
            for rol in roles_db
        ]
        return ListaRolesResponse(status="success", data=roles_dto)

