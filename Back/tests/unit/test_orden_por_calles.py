"""El orden de visita usa los tiempos reales de manejo (OSRM), no la línea recta."""

import pytest

from app.application.services.servicio_recorridos import ServicioRecorridos
from app.domain.constants.estados_logistica import TipoDistanciaEnum
from app.domain.rules.recorrido_rules import ParadaPlanificable

ORIGEN = (-31.40, -64.18)
CERCA = ParadaPlanificable("cerca", -31.401, -64.181, 1)
LEJOS = ParadaPlanificable("lejos", -31.43, -64.21, 1)


class RutasFalsas:
    """La parada «cerca» en línea recta queda lejos manejando (por ejemplo, del otro lado de una avenida sin cruce)."""

    def __init__(self):
        self.pedidos: list[list[tuple[float, float]]] = []

    async def matriz(self, puntos):
        self.pedidos.append(puntos)
        segundos = {(ORIGEN, LEJOS.punto): 60, (ORIGEN, CERCA.punto): 900, (LEJOS.punto, CERCA.punto): 60,
                    (CERCA.punto, LEJOS.punto): 900, (LEJOS.punto, ORIGEN): 900, (CERCA.punto, ORIGEN): 60}
        return [[0 if a == b else segundos[(a, b)] for b in puntos] for a in puntos]

    async def recorrido(self, puntos):
        return 4200.0, 600.0


@pytest.mark.asyncio
async def test_ordena_con_tiempos_reales_de_manejo():
    rutas = RutasFalsas()
    servicio = ServicioRecorridos(None, None, rutas=rutas)
    orden = await servicio._ordenar(ORIGEN, [CERCA, LEJOS], TipoDistanciaEnum.CORTA.value, 0.0)
    assert [p.clave for p in orden] == ["lejos", "cerca"]
    assert rutas.pedidos, "se consultó la matriz de tiempos"


@pytest.mark.asyncio
async def test_estimacion_por_calles_suma_la_atencion_en_cada_parada():
    servicio = ServicioRecorridos(None, None, rutas=RutasFalsas())
    km, minutos = await servicio._estimar_paradas(ORIGEN, [CERCA, LEJOS], TipoDistanciaEnum.CORTA.value, 0.0)
    assert km == 4.2 and minutos > 10


@pytest.mark.asyncio
async def test_sin_osrm_usa_la_distancia_estimada():
    servicio = ServicioRecorridos(None, None)
    orden = await servicio._ordenar(ORIGEN, [LEJOS, CERCA], TipoDistanciaEnum.CORTA.value, 0.0)
    assert [p.clave for p in orden][0] == "cerca"
