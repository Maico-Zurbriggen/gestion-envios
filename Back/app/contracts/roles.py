from typing import List, Optional
from pydantic import Field

from app.contracts.common import ApiModel


class RolResponse(ApiModel):
    id: int = Field(..., description="Identificador numérico del rol", examples=[1])
    nombre: str = Field(..., description="Nombre identificador del rol", examples=["SUPERADMIN"])
    descripcion: Optional[str] = Field(None, description="Descripción funcional del rol", examples=["Administrador general del sistema"])


class ListaRolesResponse(ApiModel):
    status: str = "success"
    data: List[RolResponse]

