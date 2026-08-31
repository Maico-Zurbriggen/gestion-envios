from enum import Enum, StrEnum


class RolEnum(StrEnum):
    SUPERADMIN = "SUPERADMIN"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    VENDEDOR = "VENDEDOR"
    REPARTIDOR = "REPARTIDOR"


class RolIdEnum(int, Enum):
    SUPERADMIN = 1
    ADMINISTRATIVO = 2
    VENDEDOR = 3
    REPARTIDOR = 4

