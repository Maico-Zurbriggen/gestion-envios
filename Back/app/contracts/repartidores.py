"""Contratos de los perfiles de repartidor (soporte de HU10).

HU01 da de alta usuarios con rol `REPARTIDOR`, pero para asignarles
recorridos hace falta saber desde qué sucursal salen y si hacen corta o larga
distancia (HU10 Escenario 4). Eso vive en `repartidores`, extensión 1 a 1 de
`usuarios`.
"""

from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ApiModel
from app.contracts.sucursales import SucursalData
from app.domain.constants.estados_logistica import TipoDistanciaEnum

TIPOS_REPARTO_VALIDOS = [t.value for t in TipoDistanciaEnum]


class PerfilRepartidorRequest(ApiModel):
    """Alta o modificación del perfil operativo de un repartidor."""

    sucursal_base_id: int = Field(..., gt=0, description="Sucursal desde la que sale a sus recorridos.")
    tipo_reparto: str = Field(..., description="'CORTA' (misma ciudad) o 'LARGA' (entre ciudades).")
    activo: bool = Field(True, description="Si es `false`, no se le asignan recorridos nuevos.")

    @field_validator("tipo_reparto")
    @classmethod
    def validar_tipo_reparto(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in TIPOS_REPARTO_VALIDOS:
            raise ValueError(f"Tipo de reparto inválido. Valores aceptados: {', '.join(TIPOS_REPARTO_VALIDOS)}.")
        return v


class RepartidorData(ApiModel):
    """Usuario con rol REPARTIDOR y su perfil operativo, si ya fue configurado."""

    usuario_id: UUID
    nombre: str
    dni: str
    email: str
    telefono: str
    estado_usuario: str
    perfil_configurado: bool
    sucursal_base: SucursalData | None = None
    tipo_reparto: str | None = None
    activo: bool | None = None
    disponible_para_recorridos: bool = Field(
        ...,
        description="True si tiene perfil, está activo como repartidor y su cuenta está Activa.",
    )


class ListarRepartidoresResponse(ApiModel):
    status: str = "success"
    total: int
    data: list[RepartidorData]


class RepartidorResponse(ApiModel):
    status: str = "success"
    message: str | None = None
    data: RepartidorData
