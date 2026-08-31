from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Usuario:
    id: UUID
    nombre: str
    dni: str
    email: str
    telefono: str
    password_hash: str
    rol_id: int
    estado: str = "Activo"
    requiere_cambio_password: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

