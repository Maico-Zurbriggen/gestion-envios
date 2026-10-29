import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.contracts.auth import SucursalAccesoData
from app.contracts.common import ApiModel


def normalizar_dni(v: str) -> str:
    v = v.strip()
    if not v.isdigit():
        raise ValueError("El DNI debe contener solo dígitos.")
    if len(v) < 6 or len(v) > 20:
        raise ValueError("El DNI debe tener una longitud válida.")
    return v


def normalizar_telefono(v: str) -> str:
    v = v.strip()
    if not re.match(r"^[\+]?[0-9\s\-]{6,30}$", v):
        raise ValueError("El formato de teléfono no es válido.")
    return v


class CrearEmpleadoRequest(ApiModel):
    """Alta de empleado por Superadministrador (HU01). No incluye
    contraseña: se genera automáticamente en el servicio y se devuelve una
    única vez en la respuesta (ver `EmpleadoCreadoData.password_temporal`)."""

    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre y apellido del empleado")
    dni: str = Field(..., description="DNI del empleado (solo dígitos)", examples=["35123456"])
    email: EmailStr = Field(..., description="Correo electrónico del empleado", examples=["carlos.gomez@empresa.com"])
    telefono: str = Field(..., min_length=6, max_length=30, description="Teléfono de contacto", examples=["+543564123456"])
    rol_id: int = Field(..., description="Identificador del rol a asignar", examples=[2])
    sucursal_ids: list[int] = Field(
        default_factory=list,
        description="Sucursales en las que trabaja. Vendedores y administrativos necesitan al menos una.",
    )

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, v: str) -> str:
        return normalizar_dni(v)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        return normalizar_telefono(v)


class EmpleadoCreadoData(ApiModel):
    """`password_temporal` viaja en texto plano solo en esta respuesta; el
    backend nunca vuelve a exponerla, solo persiste su hash BCrypt."""

    id: UUID
    nombre: str
    dni: str
    email: str
    telefono: str
    estado: str
    rol: str
    password_temporal: str
    sucursales: list[SucursalAccesoData] = Field(default_factory=list)


class CrearEmpleadoResponse(ApiModel):
    status: str = "success"
    message: str = "Empleado creado correctamente."
    data: EmpleadoCreadoData



# --- Gestión de usuarios del personal (listado, edición, baja y blanqueo) ---


class EmpleadoData(ApiModel):
    """Usuario del personal tal como lo ve el Superadministrador. Nunca incluye
    la contraseña ni su hash."""

    id: UUID
    nombre: str
    dni: str
    email: str
    telefono: str
    estado: str
    rol: str
    rol_id: int
    requiere_cambio_password: bool
    created_at: datetime
    updated_at: datetime
    sucursales: list[SucursalAccesoData] = Field(default_factory=list, description="Sucursales habilitadas.")


class ResumenEmpleadosData(ApiModel):
    total: int
    activos: int
    inactivos: int
    por_rol: dict[str, int]


class ListarEmpleadosData(ApiModel):
    empleados: list[EmpleadoData]
    total: int
    resumen: ResumenEmpleadosData


class ListarEmpleadosResponse(ApiModel):
    status: str = "success"
    message: str = "Usuarios obtenidos correctamente."
    data: ListarEmpleadosData


class EmpleadoResponse(ApiModel):
    status: str = "success"
    message: str = "Usuario obtenido correctamente."
    data: EmpleadoData


class ActualizarEmpleadoRequest(ApiModel):
    """Edición parcial: solo cambia lo que se envía."""

    nombre: str | None = Field(None, min_length=2, max_length=100)
    dni: str | None = None
    email: EmailStr | None = None
    telefono: str | None = Field(None, min_length=6, max_length=30)
    rol_id: int | None = None
    sucursal_ids: list[int] | None = Field(None, description="Reemplaza las sucursales habilitadas.")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        return v

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, v: str | None) -> str | None:
        return None if v is None else normalizar_dni(v)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str | None) -> str | None:
        return None if v is None else normalizar_telefono(v)

    @model_validator(mode="after")
    def validar_algun_campo(self) -> "ActualizarEmpleadoRequest":
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un dato para modificar.")
        return self


class CambiarEstadoEmpleadoRequest(ApiModel):
    estado: Literal["Activo", "Inactivo"]


class PasswordRestablecidaData(ApiModel):
    """La contraseña temporal viaja una sola vez, como en el alta."""

    id: UUID
    nombre: str
    password_temporal: str


class PasswordRestablecidaResponse(ApiModel):
    status: str = "success"
    message: str = "Contraseña restablecida. El usuario deberá cambiarla al ingresar."
    data: PasswordRestablecidaData
