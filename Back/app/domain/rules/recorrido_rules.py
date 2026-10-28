"""Reglas de dominio de la generación y edición de recorridos de reparto (HU10).

Todo es puro (sin I/O ni ORM) para poder probar el algoritmo de punta a punta
con datos armados a mano. El servicio de aplicación traduce los paquetes de la
base a `ParadaPlanificable` y aplica lo que devuelven estas funciones.

Cómo se cubren los factores que pide HU10 Escenario 1:

- **Sucursal de partida:** todo recorrido arranca en la sucursal origen; el
  reparto equitativo barre las paradas por ángulo alrededor de ella y el orden
  de visita se optimiza partiendo de ella.
- **Orientación de las calles:** dentro de una ciudad no se viaja en línea
  recta sino por calles. La distancia urbana es la de Manhattan medida sobre los
  ejes de la cuadrícula de la ciudad, rotada según `orientacion_grados` (el
  ángulo de las calles respecto del norte). Una ciudad con calles a 45° cambia
  qué paradas quedan "cerca" entre sí, y por lo tanto el orden de visita.
- **Optimización del tiempo:** el orden de visita parte del vecino más cercano
  y se mejora con 2-opt hasta que ningún intercambio acorta el recorrido; la
  duración estimada suma el viaje y el tiempo de atención de cada parada.
- **Distribución equitativa:** las paradas se ordenan por ángulo (barrido) y se
  parten en tramos contiguos minimizando la carga máxima de paquetes de un
  repartidor; cada repartidor recibe una zona geográficamente compacta.

Escenario 4 (corta / larga distancia) se resuelve en `determinar_tipo_reparto`.
"""

import math
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    MotivoAlertaRecorridoEnum,
    TipoDistanciaEnum,
)

# --- Parámetros de estimación ---

VELOCIDAD_URBANA_KMH = 25.0
"""Velocidad promedio de un repartidor de corta distancia dentro de la ciudad."""

VELOCIDAD_RUTA_KMH = 80.0
"""Velocidad promedio en ruta entre ciudades (larga distancia)."""

MINUTOS_POR_PARADA_DOMICILIO = 5
MINUTOS_POR_PARADA_SUCURSAL = 15
"""Tiempo de atención en cada parada: entregar en mano vs. descargar en una sucursal."""

FACTOR_SINUOSIDAD_RUTA = 1.25
"""Las rutas entre ciudades no son rectas: se infla la distancia geodésica."""

RADIO_TIERRA_KM = 6371.0
KM_POR_GRADO_LATITUD = 110.574
KM_POR_GRADO_LONGITUD_ECUADOR = 111.320

ORIENTACION_MINIMA_GRADOS = 0.0
ORIENTACION_MAXIMA_GRADOS = 90.0
"""Una cuadrícula es simétrica cada 90°: 0° y 90° describen la misma ciudad."""

MAX_PASADAS_2OPT = 50

# --- Estados ---

ESTADOS_PAQUETE_LISTOS_PARA_DESPACHO: set[str] = {
    EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value,
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
    EstadoPaqueteEnum.ENTREGA_FALLIDA.value,
    EstadoPaqueteEnum.EN_DEVOLUCION.value,
}
"""Paquetes que están físicamente en una sucursal esperando salir: recién
recibidos en la terminal (HU06), llegados a la sucursal de la ciudad destino
(HU11), devueltos tras una visita fallida (HU12, para reintentar) o que vuelven
al remitente porque no se retiraron a tiempo (viajan a la sucursal de origen)."""

ESTADOS_RECORRIDO_EDITABLES: set[str] = {
    EstadoRecorridoEnum.GENERADO.value,
    EstadoRecorridoEnum.EN_EDICION.value,
}
"""Un recorrido solo se edita antes de salir; una vez en curso es del repartidor (HU11)."""

ESTADOS_RECORRIDO_ACTIVOS: set[str] = ESTADOS_RECORRIDO_EDITABLES | {EstadoRecorridoEnum.EN_CURSO.value}
"""Mientras un recorrido está en alguno de estos estados, sus paquetes pendientes
no pueden asignarse a otro recorrido."""

DESCRIPCIONES_MOTIVO_ALERTA: dict[str, str] = {
    MotivoAlertaRecorridoEnum.SIN_RECORRIDO_ASIGNADO.value: "El paquete quedó fuera de todos los recorridos.",
    MotivoAlertaRecorridoEnum.SIN_REPARTIDOR_DISPONIBLE.value: (
        "No hay repartidores activos del tipo de reparto requerido en la sucursal."
    ),
    MotivoAlertaRecorridoEnum.SIN_UBICACION_DESTINO.value: (
        "El destino no tiene coordenadas: no se puede ubicar en el mapa y debe asignarse manualmente."
    ),
    MotivoAlertaRecorridoEnum.SIN_SUCURSAL_DESTINO.value: (
        "No se encontró una sucursal de destino a la cual trasladar el paquete."
    ),
    MotivoAlertaRecorridoEnum.FALTANTE_EN_DESCARGA.value: (
        "Tenía que bajar en la sucursal de destino y no apareció al controlar la descarga. Revisá su trazabilidad."
    ),
    MotivoAlertaRecorridoEnum.FALTANTE_EN_CARGA.value: (
        "No se cargó en el vehículo al controlar la carga: se quitó del recorrido y espera el próximo."
    ),
}


# --- Tipos de dato ---

Punto = tuple[float, float]
"""(latitud, longitud) en grados decimales."""


@dataclass(frozen=True)
class ParadaPlanificable:
    """Un punto que el repartidor tiene que visitar.

    `clave` identifica la parada (varios paquetes al mismo domicilio o a la
    misma sucursal comparten parada) y `cantidad_paquetes` es su peso para el
    reparto equitativo.
    """

    clave: str
    latitud: float
    longitud: float
    cantidad_paquetes: int = 1

    @property
    def punto(self) -> Punto:
        return (self.latitud, self.longitud)


FuncionDistancia = Callable[[Punto, Punto], float]


# --- Escenario 4: corta o larga distancia ---


def normalizar_lugar(nombre: str | None) -> str:
    """Compara nombres de ciudad/provincia sin tildes, mayúsculas ni espacios extra."""
    if not nombre:
        return ""
    descompuesto = unicodedata.normalize("NFKD", nombre)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def misma_ciudad(
    ciudad_a: str | None,
    provincia_a: str | None,
    ciudad_b: str | None,
    provincia_b: str | None,
) -> bool:
    """Dos ubicaciones son de la misma ciudad si coincide la ciudad y, cuando ambas
    la informan, también la provincia (hay ciudades homónimas en distintas provincias)."""
    if not normalizar_lugar(ciudad_a) or normalizar_lugar(ciudad_a) != normalizar_lugar(ciudad_b):
        return False
    if normalizar_lugar(provincia_a) and normalizar_lugar(provincia_b):
        return normalizar_lugar(provincia_a) == normalizar_lugar(provincia_b)
    return True


@dataclass(frozen=True)
class SucursalUbicada:
    """Lo mínimo de una sucursal que necesitan las reglas de reparto."""

    id: int
    ciudad: str | None
    provincia: str | None
    latitud: float | None = None
    longitud: float | None = None

    @property
    def punto(self) -> Punto | None:
        if self.latitud is None or self.longitud is None:
            return None
        return (self.latitud, self.longitud)


def elegir_sucursal_de_entrega(
    ciudad_destino: str | None,
    provincia_destino: str | None,
    punto_destino: Punto | None,
    sucursales: Sequence[SucursalUbicada],
    sucursal_actual_id: int | None = None,
) -> int | None:
    """Sucursal desde la que sale el repartidor de corta distancia hacia un domicilio.

    1. Si la sucursal actual está en la ciudad del destino, es ella (no tiene
       sentido trasladar el paquete a otra sucursal de la misma ciudad).
    2. Si no, una sucursal de esa ciudad: la más cercana al domicilio si hay
       coordenadas, o la de menor id.
    3. Si la ciudad no tiene sucursal, la más cercana al domicilio (atiende las
       localidades vecinas).
    4. Sin sucursal en la ciudad ni coordenadas para medir: `None`.
    """
    en_ciudad = [s for s in sucursales if misma_ciudad(s.ciudad, s.provincia, ciudad_destino, provincia_destino)]
    if en_ciudad:
        if any(s.id == sucursal_actual_id for s in en_ciudad):
            return sucursal_actual_id
        return _mas_cercana(en_ciudad, punto_destino) or min(s.id for s in en_ciudad)
    return _mas_cercana(sucursales, punto_destino)


def _mas_cercana(sucursales: Sequence[SucursalUbicada], punto: Punto | None) -> int | None:
    if punto is None:
        return None
    con_ubicacion = [s for s in sucursales if s.punto is not None]
    if not con_ubicacion:
        return None
    return min(con_ubicacion, key=lambda s: (distancia_haversine_km(punto, s.punto), s.id)).id


def determinar_tipo_reparto(
    tipo_entrega: str,
    sucursal_entrega_id: int | None,
    sucursal_actual_id: int | None,
    destino_en_misma_ciudad: bool = False,
) -> str | None:
    """Decide qué tipo de recorrido necesita un paquete que está en una sucursal (HU10 Escenario 4).

    `sucursal_entrega_id` es la última sucursal de la red antes del
    destinatario: la elegida para el retiro, o la que atiende el domicilio
    (`elegir_sucursal_de_entrega`).

    - Retiro en la misma sucursal donde ya está: `None`, no hay nada que repartir.
    - Retiro en otra sucursal: `LARGA` (se deja en esa sucursal).
    - Domicilio atendido por la sucursal actual: `CORTA`.
    - Domicilio atendido por otra sucursal: `LARGA`; desde allá saldrá en un
      recorrido corto.
    - Domicilio sin sucursal que lo atienda identificable: se decide por ciudad.
    """
    tipo = (tipo_entrega or "").strip().lower()
    if tipo == "sucursal":
        if sucursal_entrega_id is not None and sucursal_entrega_id == sucursal_actual_id:
            return None
        return TipoDistanciaEnum.LARGA.value
    if tipo == "domicilio":
        if sucursal_entrega_id is None:
            return TipoDistanciaEnum.CORTA.value if destino_en_misma_ciudad else TipoDistanciaEnum.LARGA.value
        if sucursal_entrega_id == sucursal_actual_id:
            return TipoDistanciaEnum.CORTA.value
        return TipoDistanciaEnum.LARGA.value
    return None


def paquete_listo_para_despacho(estado: str | None) -> bool:
    return (estado or "").strip() in ESTADOS_PAQUETE_LISTOS_PARA_DESPACHO


def estado_paquete_al_iniciar(tipo_distancia: str) -> str:
    """Estado al que pasa cada paquete cuando el recorrido sale de la sucursal."""
    if tipo_distancia == TipoDistanciaEnum.CORTA.value:
        return EstadoPaqueteEnum.EN_REPARTO.value
    return EstadoPaqueteEnum.EN_TRANSITO.value


def vuelve_a_la_sucursal(tipo_distancia: str) -> bool:
    """El repartidor urbano vuelve a su sucursal al terminar; el de larga distancia
    termina el recorrido en la última sucursal donde descarga."""
    return tipo_distancia == TipoDistanciaEnum.CORTA.value


# --- Distancias ---


def distancia_haversine_km(a: Punto, b: Punto) -> float:
    """Distancia geodésica (en línea recta sobre la Tierra) entre dos puntos."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(min(1.0, math.sqrt(h)))


def distancia_urbana_km(a: Punto, b: Punto, orientacion_grados: float = 0.0) -> float:
    """Distancia recorriendo calles de una cuadrícula orientada `orientacion_grados`.

    Proyecta el desplazamiento a kilómetros (aproximación equirectangular,
    exacta de sobra a escala de una ciudad), lo rota a los ejes de la
    cuadrícula y suma los tramos sobre cada eje (métrica de Manhattan).
    """
    latitud_media = math.radians((a[0] + b[0]) / 2)
    dx = (b[1] - a[1]) * KM_POR_GRADO_LONGITUD_ECUADOR * math.cos(latitud_media)
    dy = (b[0] - a[0]) * KM_POR_GRADO_LATITUD
    theta = math.radians(orientacion_grados)
    eje_u = dx * math.cos(theta) + dy * math.sin(theta)
    eje_v = -dx * math.sin(theta) + dy * math.cos(theta)
    return abs(eje_u) + abs(eje_v)


def distancia_ruta_km(a: Punto, b: Punto) -> float:
    """Distancia estimada por ruta entre ciudades."""
    return distancia_haversine_km(a, b) * FACTOR_SINUOSIDAD_RUTA


def funcion_distancia(tipo_distancia: str, orientacion_grados: float = 0.0) -> FuncionDistancia:
    """Métrica que corresponde a cada tipo de recorrido."""
    if tipo_distancia == TipoDistanciaEnum.CORTA.value:
        return lambda a, b: distancia_urbana_km(a, b, orientacion_grados)
    return distancia_ruta_km


# --- Escenario 1: distribución equitativa ---


def angulo_desde(origen: Punto, punto: Punto) -> float:
    """Ángulo (radianes, 0..2π) del punto visto desde el origen, para el barrido."""
    dx = (punto[1] - origen[1]) * math.cos(math.radians(origen[0]))
    dy = punto[0] - origen[0]
    return math.atan2(dy, dx) % (2 * math.pi)


def ordenar_por_barrido(origen: Punto, paradas: Sequence[ParadaPlanificable]) -> list[ParadaPlanificable]:
    """Ordena las paradas por ángulo alrededor del origen, empezando después del
    mayor hueco angular: así ninguna zona queda partida entre el principio y el
    final de la vuelta."""
    ordenadas = sorted(paradas, key=lambda p: (angulo_desde(origen, p.punto), p.clave))
    if len(ordenadas) < 2:
        return ordenadas

    angulos = [angulo_desde(origen, p.punto) for p in ordenadas]
    huecos = [(angulos[(i + 1) % len(angulos)] - angulos[i]) % (2 * math.pi) for i in range(len(angulos))]
    inicio = (max(range(len(huecos)), key=lambda i: huecos[i]) + 1) % len(ordenadas)
    return ordenadas[inicio:] + ordenadas[:inicio]


def particionar_equitativamente(cargas: Sequence[int], cantidad_grupos: int) -> list[int]:
    """Parte una secuencia de cargas en tramos contiguos minimizando la carga máxima.

    Es el problema clásico de "partición lineal", resuelto con programación
    dinámica. Devuelve los índices de inicio de cada tramo (el primero siempre
    es 0). Si hay menos elementos que grupos, cada elemento queda en su tramo.
    """
    n = len(cargas)
    if cantidad_grupos <= 0:
        raise ValueError("La cantidad de grupos debe ser positiva.")
    if n == 0:
        return []
    k = min(cantidad_grupos, n)

    acumuladas = [0]
    for carga in cargas:
        acumuladas.append(acumuladas[-1] + carga)

    def carga_tramo(i: int, j: int) -> int:
        return acumuladas[j] - acumuladas[i]

    infinito = float("inf")
    # mejor[g][j]: menor carga máxima posible repartiendo los primeros j elementos en g tramos no vacíos
    mejor = [[infinito] * (n + 1) for _ in range(k + 1)]
    corte = [[0] * (n + 1) for _ in range(k + 1)]
    mejor[0][0] = 0
    for g in range(1, k + 1):
        for j in range(g, n + 1):
            for i in range(g - 1, j):
                candidato = max(mejor[g - 1][i], carga_tramo(i, j))
                if candidato < mejor[g][j]:
                    mejor[g][j] = candidato
                    corte[g][j] = i

    inicios: list[int] = []
    j = n
    for g in range(k, 0, -1):
        i = corte[g][j]
        inicios.append(i)
        j = i
    return list(reversed(inicios))


def repartir_paradas_equitativamente(
    origen: Punto,
    paradas: Sequence[ParadaPlanificable],
    cantidad_repartidores: int,
) -> list[list[ParadaPlanificable]]:
    """Asigna las paradas a `cantidad_repartidores` zonas con carga de paquetes pareja.

    Devuelve siempre `cantidad_repartidores` listas; quedan vacías las que
    sobran si hay más repartidores que paradas.
    """
    if cantidad_repartidores <= 0:
        raise ValueError("Se necesita al menos un repartidor para repartir paradas.")

    barrido = ordenar_por_barrido(origen, paradas)
    inicios = particionar_equitativamente([p.cantidad_paquetes for p in barrido], cantidad_repartidores)

    grupos: list[list[ParadaPlanificable]] = []
    for indice, inicio in enumerate(inicios):
        fin = inicios[indice + 1] if indice + 1 < len(inicios) else len(barrido)
        grupos.append(list(barrido[inicio:fin]))
    while len(grupos) < cantidad_repartidores:
        grupos.append([])
    return grupos


# --- Escenario 1: optimización del orden de visita ---


def costo_recorrido(
    origen: Punto,
    paradas: Sequence[ParadaPlanificable],
    distancia: FuncionDistancia,
    vuelve_al_origen: bool = True,
) -> float:
    """Kilómetros totales de visitar las paradas en ese orden desde el origen."""
    total = 0.0
    actual = origen
    for parada in paradas:
        total += distancia(actual, parada.punto)
        actual = parada.punto
    if vuelve_al_origen and paradas:
        total += distancia(actual, origen)
    return total


def ordenar_paradas(
    origen: Punto,
    paradas: Sequence[ParadaPlanificable],
    distancia: FuncionDistancia,
    vuelve_al_origen: bool = True,
) -> list[ParadaPlanificable]:
    """Orden de visita que minimiza la distancia: vecino más cercano + mejora 2-opt.

    2-opt invierte un tramo del recorrido cada vez que eso lo acorta (elimina
    los "cruces"), hasta que ningún intercambio mejora o se agotan las pasadas.
    Los empates se resuelven por `clave` para que el resultado sea determinista.
    """
    pendientes = list(paradas)
    ruta: list[ParadaPlanificable] = []
    actual = origen
    while pendientes:
        siguiente = min(pendientes, key=lambda p: (distancia(actual, p.punto), p.clave))
        ruta.append(siguiente)
        pendientes.remove(siguiente)
        actual = siguiente.punto

    mejor_costo = costo_recorrido(origen, ruta, distancia, vuelve_al_origen)
    for _ in range(MAX_PASADAS_2OPT):
        mejorado = False
        for i in range(len(ruta) - 1):
            for j in range(i + 1, len(ruta)):
                candidata = ruta[:i] + ruta[i : j + 1][::-1] + ruta[j + 1 :]
                costo = costo_recorrido(origen, candidata, distancia, vuelve_al_origen)
                if costo < mejor_costo - 1e-9:
                    ruta, mejor_costo, mejorado = candidata, costo, True
        if not mejorado:
            break
    return ruta


def estimar_recorrido(
    origen: Punto,
    paradas: Sequence[ParadaPlanificable],
    tipo_distancia: str,
    orientacion_grados: float = 0.0,
    paradas_sin_ubicacion: int = 0,
) -> tuple[float, int]:
    """Distancia (km) y duración (min) estimadas del recorrido en el orden dado.

    `paradas_sin_ubicacion` son paradas agregadas a mano cuyo destino no tiene
    coordenadas: no suman kilómetros (no se pueden medir) pero sí su tiempo de
    atención.
    """
    distancia = funcion_distancia(tipo_distancia, orientacion_grados)
    km = costo_recorrido(origen, paradas, distancia, vuelve_a_la_sucursal(tipo_distancia))

    if tipo_distancia == TipoDistanciaEnum.CORTA.value:
        velocidad, minutos_parada = VELOCIDAD_URBANA_KMH, MINUTOS_POR_PARADA_DOMICILIO
    else:
        velocidad, minutos_parada = VELOCIDAD_RUTA_KMH, MINUTOS_POR_PARADA_SUCURSAL

    cantidad_paradas = len(paradas) + paradas_sin_ubicacion
    minutos = km / velocidad * 60 + cantidad_paradas * minutos_parada
    return round(km, 2), int(round(minutos))


def planificar_recorridos(
    origen: Punto,
    paradas: Sequence[ParadaPlanificable],
    cantidad_repartidores: int,
    tipo_distancia: str,
    orientacion_grados: float = 0.0,
) -> list[list[ParadaPlanificable]]:
    """Generación automática completa (HU10 Escenario 1): reparte las paradas en
    zonas equitativas y ordena cada zona para minimizar el tiempo."""
    distancia = funcion_distancia(tipo_distancia, orientacion_grados)
    vuelve = vuelve_a_la_sucursal(tipo_distancia)
    return [
        ordenar_paradas(origen, grupo, distancia, vuelve) if grupo else []
        for grupo in repartir_paradas_equitativamente(origen, paradas, cantidad_repartidores)
    ]
