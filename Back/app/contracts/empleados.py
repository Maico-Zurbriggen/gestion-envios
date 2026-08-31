import re
from uuid import UUID
from pydantic import EmailStr, Field, field_validator
from app.contracts.common import ApiModel


class CrearEmpleadoRequest(ApiModel):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre y apellido del empleado")
    dni: str = Field(..., description="DNI del empleado (solo dígitos)", examples=["35123456"])
    email: EmailStr = Field(..., description="Correo electrónico del empleado", examples=["carlos.gomez@empresa.com"])
    telefono: str = Field(..., min_length=6, max_length=30, description="Teléfono de contacto", examples=["+543564123456"])
    rol_id: int = Field(..., description="Identificador del rol a asignar", examples=[2])

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El DNI debe contener solo dígitos.")
        if len(v) < 6 or len(v) > 20:
            raise ValueError("El DNI debe tener una longitud válida.")
        return v

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[\+]?[0-9\s\-]{6,30}$", v):
            raise ValueError("El formato de teléfono no es válido.")
        return v


class EmpleadoCreadoData(ApiModel):
    id: UUID
    nombre: str
    dni: str
    email: str
    telefono: str
    estado: str
    rol: str
    password_temporal: str


class CrearEmpleadoResponse(ApiModel):
    status: str = "success"
    message: str = "Empleado creado correctamente."
    data: EmpleadoCreadoData

