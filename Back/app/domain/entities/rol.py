from dataclasses import dataclass
from typing import Optional


@dataclass
class Rol:
    id: int
    nombre: str
    descripcion: Optional[str] = None

