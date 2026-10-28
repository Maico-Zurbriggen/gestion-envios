"""Reglas de administración de usuarios del personal (listado, edición, baja).

Funciones puras: no tocan la base. Protegen dos cosas:
- que nadie se quite a sí mismo el acceso (cambiando su rol o dándose de baja), y
- que el sistema nunca quede sin un Superadministrador activo.
"""

from typing import Any

ESTADO_ACTIVO = "Activo"
ESTADO_INACTIVO = "Inactivo"
ESTADOS_EMPLEADO = (ESTADO_ACTIVO, ESTADO_INACTIVO)
ROL_SUPERADMIN = "SUPERADMIN"


def validar_cambios_propios(*, es_uno_mismo: bool, cambia_rol: bool, cambia_estado: bool) -> list[dict[str, Any]]:
    """Errores si el usuario intenta cambiar su propio rol o su estado."""
    if not es_uno_mismo:
        return []
    errores = []
    if cambia_rol:
        errores.append({"field": "rol_id", "message": "No podés cambiar tu propio rol. Pedile a otro Superadministrador que lo haga."})
    if cambia_estado:
        errores.append({"field": "estado", "message": "No podés dar de baja tu propio usuario."})
    return errores


def deja_de_ser_superadmin_activo(*, rol_actual: str, estado_actual: str, rol_nuevo: str, estado_nuevo: str) -> bool:
    """`True` si el cambio quita a un Superadministrador activo de ese conjunto."""
    era = rol_actual == ROL_SUPERADMIN and estado_actual == ESTADO_ACTIVO
    sigue = rol_nuevo == ROL_SUPERADMIN and estado_nuevo == ESTADO_ACTIVO
    return era and not sigue


def coincide_busqueda(texto: str, *campos: str | None) -> bool:
    """Búsqueda simple sin distinguir mayúsculas en nombre, DNI, email o teléfono."""
    buscado = (texto or "").strip().lower()
    if not buscado:
        return True
    return any(buscado in (campo or "").lower() for campo in campos)
