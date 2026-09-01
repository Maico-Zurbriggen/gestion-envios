from dataclasses import dataclass
from typing import Optional


# Nota: sin uso actual, ídem `usuario.py` — ver ese archivo.
@dataclass
class Rol:
    id: int
    nombre: str
    descripcion: Optional[str] = None

