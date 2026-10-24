import itertools
import math

import pytest

from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    MotivoAlertaRecorridoEnum,
    TipoDistanciaEnum,
)
from app.domain.rules.recorrido_rules import (
    DESCRIPCIONES_MOTIVO_ALERTA,
    FACTOR_SINUOSIDAD_RUTA,
    MINUTOS_POR_PARADA_DOMICILIO,
    ParadaPlanificable,
    costo_recorrido,
    determinar_tipo_reparto,
    distancia_haversine_km,
    distancia_urbana_km,
    estado_paquete_al_iniciar,
    estimar_recorrido,
    funcion_distancia,
    misma_ciudad,
    ordenar_paradas,
    ordenar_por_barrido,
    paquete_listo_para_despacho,
    particionar_equitativamente,
    planificar_recorridos,
    repartir_paradas_equitativamente,
    validar_orientacion,
)

CORTA = TipoDistanciaEnum.CORTA.value
LARGA = TipoDistanciaEnum.LARGA.value
ORIGEN = (-31.4167, -64.1833)  # Córdoba


def _parada(clave: str, dlat: float, dlon: float, paquetes: int = 1) -> ParadaPlanificable:
    return ParadaPlanificable(clave=clave, latitud=ORIGEN[0] + dlat, longitud=ORIGEN[1] + dlon, cantidad_paquetes=paquetes)


# --- Escenario 4: tipos de reparto ---


def test_domicilio_en_la_misma_ciudad_es_corta_distancia():
    assert determinar_tipo_reparto("domicilio", True, None, 1) == CORTA


def test_domicilio_en_otra_ciudad_es_larga_distancia():
    assert determinar_tipo_reparto("domicilio", False, None, 1) == LARGA


def test_retiro_en_otra_sucursal_es_larga_distancia():
    assert determinar_tipo_reparto("sucursal", False, 2, 1) == LARGA


def test_retiro_en_la_sucursal_donde_ya_esta_no_se_reparte():
    assert determinar_tipo_reparto("sucursal", True, 1, 1) is None


def test_tipo_de_entrega_desconocido_no_se_reparte():
    assert determinar_tipo_reparto("drone", True, None, 1) is None


def test_misma_ciudad_ignora_tildes_y_exige_provincia_si_ambas_la_informan():
    assert misma_ciudad("Córdoba", "Córdoba", " cordoba ", "CORDOBA")
    assert misma_ciudad("Rosario", None, "rosario", "Santa Fe")
    assert not misma_ciudad("San Martín", "Mendoza", "San Martin", "Buenos Aires")
    assert not misma_ciudad(None, None, None, None)


def test_estados_listos_para_despacho():
    assert paquete_listo_para_despacho(EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value)
    assert paquete_listo_para_despacho(EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value)
    assert paquete_listo_para_despacho(EstadoPaqueteEnum.ENTREGA_FALLIDA.value)
    assert not paquete_listo_para_despacho("Pendiente")
    assert not paquete_listo_para_despacho(EstadoPaqueteEnum.EN_REPARTO.value)
    assert not paquete_listo_para_despacho(None)


def test_estado_al_iniciar_segun_tipo():
    assert estado_paquete_al_iniciar(CORTA) == EstadoPaqueteEnum.EN_REPARTO.value
    assert estado_paquete_al_iniciar(LARGA) == EstadoPaqueteEnum.EN_TRANSITO.value


def test_todos_los_motivos_de_alerta_tienen_descripcion():
    assert set(DESCRIPCIONES_MOTIVO_ALERTA) == {m.value for m in MotivoAlertaRecorridoEnum}


@pytest.mark.parametrize("valor, esperado", [(0, True), (45, True), (89.9, True), (90, False), (-1, False)])
def test_validar_orientacion(valor, esperado):
    assert validar_orientacion(valor) is esperado


# --- Distancias y orientación de las calles ---


def test_haversine_cordoba_rosario_aprox_400_km():
    rosario = (-32.9587, -60.6931)
    assert 350 < distancia_haversine_km(ORIGEN, rosario) < 420


def test_distancia_urbana_es_manhattan_sobre_la_cuadricula():
    # 1 km al norte y 1 km al este con calles norte-sur: 2 km por calles
    destino = (ORIGEN[0] + 1 / 110.574, ORIGEN[1] + 1 / (111.320 * math.cos(math.radians(ORIGEN[0]))))
    assert distancia_urbana_km(ORIGEN, destino, 0) == pytest.approx(2.0, rel=1e-3)
    # Con la cuadrícula a 45° ese mismo punto queda en diagonal sobre un eje: √2 km
    assert distancia_urbana_km(ORIGEN, destino, 45) == pytest.approx(math.sqrt(2), rel=1e-3)


def test_distancia_urbana_nunca_es_menor_que_la_recta():
    destino = (ORIGEN[0] + 0.02, ORIGEN[1] - 0.03)
    recta = distancia_haversine_km(ORIGEN, destino)
    for orientacion in (0, 15, 30, 60, 89):
        assert distancia_urbana_km(ORIGEN, destino, orientacion) >= recta * 0.999


def test_funcion_distancia_por_tipo():
    destino = (-32.9587, -60.6931)
    assert funcion_distancia(LARGA)(ORIGEN, destino) == pytest.approx(
        distancia_haversine_km(ORIGEN, destino) * FACTOR_SINUOSIDAD_RUTA
    )
    assert funcion_distancia(CORTA, 30)(ORIGEN, destino) == pytest.approx(distancia_urbana_km(ORIGEN, destino, 30))


def test_la_orientacion_de_las_calles_cambia_el_orden_de_visita():
    """Escenario 1: la orientación de las calles influye en el recorrido generado."""
    paradas = [_parada("A", 0.010, 0.000), _parada("B", 0.007, 0.007), _parada("C", 0.000, 0.0115)]
    orden_0 = [p.clave for p in ordenar_paradas(ORIGEN, paradas, funcion_distancia(CORTA, 0), vuelve_al_origen=False)]
    orden_45 = [
        p.clave for p in ordenar_paradas(ORIGEN, paradas, funcion_distancia(CORTA, 45), vuelve_al_origen=False)
    ]
    assert sorted(orden_0) == sorted(orden_45) == ["A", "B", "C"]
    assert orden_0 != orden_45


# --- Distribución equitativa ---


def test_particion_minimiza_la_carga_maxima():
    inicios = particionar_equitativamente([1, 1, 1, 1, 1, 1], 3)
    assert inicios == [0, 2, 4]

    inicios = particionar_equitativamente([10, 1, 1], 3)
    assert inicios == [0, 1, 2]  # ningún tramo vacío


def test_particion_con_mas_grupos_que_elementos():
    assert particionar_equitativamente([3, 4], 5) == [0, 1]
    assert particionar_equitativamente([], 3) == []


def test_particion_rechaza_cero_grupos():
    with pytest.raises(ValueError):
        particionar_equitativamente([1], 0)


def test_particion_es_optima_contra_fuerza_bruta():
    cargas = [3, 1, 4, 1, 5, 9, 2, 6]
    k = 3
    inicios = particionar_equitativamente(cargas, k)
    tramos = [cargas[a:b] for a, b in zip(inicios, inicios[1:] + [len(cargas)])]
    maximo = max(sum(t) for t in tramos)

    mejor = min(
        max(sum(cargas[a:b]) for a, b in zip((0, *cortes), (*cortes, len(cargas))))
        for cortes in itertools.combinations(range(1, len(cargas)), k - 1)
    )
    assert maximo == mejor


def test_barrido_no_parte_una_zona_entre_principio_y_fin():
    # Dos grupos bien separados: al norte y al sur. El barrido arranca después del mayor hueco.
    norte = [_parada(f"N{i}", 0.02, -0.002 + i * 0.002) for i in range(3)]
    sur = [_parada(f"S{i}", -0.02, -0.002 + i * 0.002) for i in range(3)]
    claves = [p.clave[0] for p in ordenar_por_barrido(ORIGEN, norte + sur)]
    assert claves in (list("NNNSSS"), list("SSSNNN"))


def test_reparto_equitativo_en_paquetes_y_zonas_compactas():
    """Escenario 1: distribución aproximadamente equitativa según la cantidad de repartidores."""
    norte = [_parada(f"N{i}", 0.02 + i * 0.001, 0.001 * i) for i in range(4)]
    sur = [_parada(f"S{i}", -0.02 - i * 0.001, 0.001 * i) for i in range(4)]
    grupos = repartir_paradas_equitativamente(ORIGEN, norte + sur, 2)

    assert [len(g) for g in grupos] == [4, 4]
    for grupo in grupos:
        assert len({p.clave[0] for p in grupo}) == 1  # cada repartidor recibe una sola zona


def test_reparto_pondera_por_cantidad_de_paquetes():
    paradas = [_parada("A", 0.01, 0, paquetes=6), _parada("B", 0, 0.01), _parada("C", -0.01, 0), _parada("D", 0, -0.01)]
    grupos = repartir_paradas_equitativamente(ORIGEN, paradas, 2)
    cargas = sorted(sum(p.cantidad_paquetes for p in g) for g in grupos)
    assert cargas == [3, 6]


def test_reparto_con_mas_repartidores_que_paradas_deja_grupos_vacios():
    grupos = repartir_paradas_equitativamente(ORIGEN, [_parada("A", 0.01, 0)], 3)
    assert len(grupos) == 3
    assert sum(len(g) for g in grupos) == 1


def test_reparto_sin_repartidores_falla():
    with pytest.raises(ValueError):
        repartir_paradas_equitativamente(ORIGEN, [], 0)


# --- Optimización del tiempo ---


def test_ordenar_paradas_mejora_o_iguala_cualquier_orden_y_no_pierde_paradas():
    paradas = [
        _parada("A", 0.010, 0.010),
        _parada("B", -0.010, 0.010),
        _parada("C", 0.010, -0.010),
        _parada("D", -0.010, -0.010),
        _parada("E", 0.000, 0.015),
    ]
    distancia = funcion_distancia(CORTA, 0)
    ruta = ordenar_paradas(ORIGEN, paradas, distancia)

    assert sorted(p.clave for p in ruta) == ["A", "B", "C", "D", "E"]
    optimo = min(costo_recorrido(ORIGEN, list(perm), distancia) for perm in itertools.permutations(paradas))
    assert costo_recorrido(ORIGEN, ruta, distancia) <= optimo * 1.10


def test_2opt_elimina_cruces():
    # Cuadrado: el orden con cruce A-C-B-D es peor que el perímetro
    paradas = [_parada("A", 0.01, 0.01), _parada("C", -0.01, -0.01), _parada("B", 0.01, -0.01), _parada("D", -0.01, 0.01)]
    distancia = funcion_distancia(LARGA)
    ruta = ordenar_paradas(ORIGEN, paradas, distancia)
    assert costo_recorrido(ORIGEN, ruta, distancia) < costo_recorrido(ORIGEN, paradas, distancia)


def test_ordenar_sin_paradas():
    assert ordenar_paradas(ORIGEN, [], funcion_distancia(CORTA)) == []


def test_estimacion_suma_viaje_y_atencion():
    paradas = [_parada("A", 0.01, 0.0)]
    km, minutos = estimar_recorrido(ORIGEN, paradas, CORTA, 0)
    assert km == pytest.approx(round(2 * 0.01 * 110.574, 2), rel=1e-3)  # ida y vuelta
    assert minutos == round(km / 25 * 60 + MINUTOS_POR_PARADA_DOMICILIO)


def test_estimacion_cuenta_paradas_sin_ubicacion_solo_en_tiempo():
    km_sin, min_sin = estimar_recorrido(ORIGEN, [], CORTA, paradas_sin_ubicacion=2)
    assert km_sin == 0
    assert min_sin == 2 * MINUTOS_POR_PARADA_DOMICILIO


def test_larga_distancia_no_vuelve_a_la_sucursal():
    destino = [ParadaPlanificable("R", -32.9587, -60.6931)]
    km, _ = estimar_recorrido(ORIGEN, destino, LARGA)
    assert km == pytest.approx(distancia_haversine_km(ORIGEN, destino[0].punto) * FACTOR_SINUOSIDAD_RUTA, rel=1e-3)


def test_planificar_recorridos_reparte_y_ordena():
    paradas = [_parada(f"P{i}", 0.01 * math.cos(i), 0.01 * math.sin(i)) for i in range(9)]
    grupos = planificar_recorridos(ORIGEN, paradas, 3, CORTA, 20)
    assert len(grupos) == 3
    assert sorted(p.clave for g in grupos for p in g) == sorted(p.clave for p in paradas)
    assert [len(g) for g in grupos] == [3, 3, 3]
