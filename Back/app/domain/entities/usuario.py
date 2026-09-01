from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


# Nota: los servicios actuales trabajan directamente con
# `infrastructure/db/models.py:UsuarioModel` (SQLAlchemy), no con esta
# dataclase. Queda del scaffolding inicial de la arquitectura como punto de
# partida si en el futuro se separa el dominio del ORM (ver
# Back/docs/01-arquitectura/capas-y-estructura.md).
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

