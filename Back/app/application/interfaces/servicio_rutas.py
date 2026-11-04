from typing import Protocol

Punto = tuple[float, float]
"""(latitud, longitud)."""


class IServicioRutas(Protocol):
    """Tiempos y distancias reales de manejo por calles y rutas (OSRM)."""

    async def matriz(self, puntos: list[Punto]) -> list[list[float]] | None:
        """Segundos de manejo entre cada par de puntos, o `None` si no hay cálculo por calles."""
        ...

    async def recorrido(self, puntos: list[Punto]) -> tuple[float, float] | None:
        """Metros y segundos de manejo pasando por los puntos en orden, o `None` si no hay cálculo por calles."""
        ...
