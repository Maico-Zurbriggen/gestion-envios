from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_servicio_roles
from app.application.interfaces.servicio_roles import IServicioRoles
from app.contracts.roles import ListaRolesResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get(
    "",
    response_model=ListaRolesResponse,
    status_code=status.HTTP_200_OK,
    summary="Listado de roles del sistema",
    description="Retorna la lista completa de roles disponibles junto con sus números de identificación (IDs) y descripciones para su uso en el Frontend.",
)
async def listar_roles(
    servicio_roles: IServicioRoles = Depends(get_servicio_roles),
) -> ListaRolesResponse:
    """Endpoint para obtener todos los roles y sus identificadores numéricos."""
    return await servicio_roles.listar_roles()

