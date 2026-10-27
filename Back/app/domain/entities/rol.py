from dataclasses import dataclass


# Nota: sin uso actual, ídem `usuario.py` — ver ese archivo.
@dataclass
class Rol:
    id: int
    nombre: str
    descripcion: str | None = None

