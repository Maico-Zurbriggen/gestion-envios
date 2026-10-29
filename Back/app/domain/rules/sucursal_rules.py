"""Acceso por sucursal: cada usuario del personal trabaja en las sucursales que tiene habilitadas."""

from collections.abc import Iterable
from typing import Any

from app.domain.constants.roles import RolEnum


def ve_todas_las_sucursales(rol: str | None) -> bool:
    """El Superadministrador entra en todas (también en las inactivas, para prepararlas)."""
    return rol == RolEnum.SUPERADMIN.value


def sucursales_permitidas(rol: str | None, asignadas: Iterable[Any], todas: Iterable[Any]) -> list[Any]:
    """Sucursales a las que puede entrar: todas para el Superadministrador; si no, las activas asignadas."""
    if ve_todas_las_sucursales(rol):
        return sorted(todas, key=lambda s: s.nombre)
    return sorted((s for s in asignadas if getattr(s, "activa", True)), key=lambda s: s.nombre)


def requiere_sucursales(rol: str | None) -> bool:
    """Todo el personal salvo el Superadministrador pertenece a sucursales concretas."""
    return rol in (RolEnum.ADMINISTRATIVO.value, RolEnum.VENDEDOR.value, RolEnum.REPARTIDOR.value)


def una_sola_sucursal(rol: str | None) -> bool:
    """El repartidor pertenece a una sola sucursal: es su base, de donde sale a repartir."""
    return rol == RolEnum.REPARTIDOR.value
