# HU09 — Sucursales disponibles para retiro

> Yo como usuario que espera un paquete deseo visualizar las sucursales disponibles para retiro cuando el envío no es a domicilio, para conocer dónde puedo retirar el paquete.

Prioridad: **Media** · Estimación: **5 SP** · Contrato orientado a frontend: [`Back/Contrato/endpoints_frontend.md`, sección 10](../../Contrato/endpoints_frontend.md).

## Endpoints

| Método | Ruta | Autenticación |
|:---|:---|:---|
| `GET` | `/api/v1/sucursales?provincia=&ciudad=` | No (público) |
| `GET` | `/api/v1/sucursales/opciones-retiro/{token}` | No (público) |

Router: [`app/api/v1/routers/sucursales.py`](../../app/api/v1/routers/sucursales.py).

Los dos son públicos, igual que la consulta de seguimiento de HU04: el criterio de aceptación dice *"desde la experiencia pública"*, y quien espera un paquete no tiene usuario en el sistema.

## Las dos mitades de la historia

El criterio de aceptación tiene una condición y un resultado, y cada uno se resuelve con un endpoint distinto:

- *"…CUANDO el usuario consulta las opciones disponibles…"* → **`GET /sucursales`** con filtros. Es el catálogo de la red: quien todavía no tiene un envío (o está decidiendo adónde mandarlo) explora las sucursales de su provincia o ciudad.
- *"DADO que el envío se gestiona para retiro y no para entrega a domicilio… ENTONCES el sistema muestra las sucursales disponibles para el retiro **del paquete**"* → **`GET /sucursales/opciones-retiro/{token}`**. Acá la respuesta es específica de *ese* envío: cuál es su sucursal, si el paquete ya llegó y qué hay que llevar para retirarlo.

El segundo es el que cumple el escenario completo; el primero es el soporte genérico que el frontend ya venía consumiendo desde HU03.

## `GET /sucursales` — filtros, sin romper lo que ya existía

El endpoint ya existía (alimentaba el selector de "retiro en sucursal" del formulario de HU03 y la pantalla de sucursales del frontend). HU09 le agrega dos query params **opcionales**:

```http
GET /api/v1/sucursales?provincia=Santa Fe&ciudad=Rosario
```

- Sin parámetros, el comportamiento y la forma de la respuesta son **idénticos** a los anteriores a HU09. Esto es deliberado: el frontend ya consume este endpoint sin filtros (`front/src/features/shipments/services/shipmentsApi.ts`) y no había razón para forzar un cambio del lado del cliente.
- La comparación es **case-insensitive y tolerante a espacios** (`func.lower()` en `RepositorioSucursales.listar_todas`, más `.strip()`): `"  santa fe  "` encuentra `"Santa Fe"`. Un usuario público tipeando el nombre de su provincia no debería pelearse con las mayúsculas.
- Una zona sin sucursales devuelve `200` con `data: []`, no un `404`. "No hay sucursales en Ushuaia" es una respuesta válida a una pregunta válida, no un error.

No hay paginación: el catálogo es chico y fijo (6 sucursales sembradas, sin endpoint de alta).

## `GET /sucursales/opciones-retiro/{token}` — la respuesta específica del envío

Recibe el mismo `token_seguimiento` que la vista pública de HU04 (`ENV-XXXXXXXXXX`), así que el usuario no necesita ningún dato nuevo: ya lo recibió por email con HU05.

La respuesta trae cuatro bloques:

| Campo | Para qué |
|:---|:---|
| `aplica_retiro` + `motivo_no_aplica` | Si el envío se retira por sucursal o no (la condición del escenario) |
| `sucursal_asignada` | El punto de retiro concreto del envío, con dirección y coordenadas para el mapa |
| `sucursales_disponibles` | La asignada **primero**, y después las otras de la misma ciudad |
| `paquetes` | El estado de cada paquete y si ya se puede ir a buscar |
| `requisitos_retiro` | Qué documentación hay que llevar |

### Un envío a domicilio responde `200`, no un error

Si `tipo_entrega` es `"domicilio"`, la respuesta es `200 OK` con `aplica_retiro: false`, el motivo explicado, y `sucursal_asignada: null` / `sucursales_disponibles: []` / `paquetes: []`:

```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-ZPC5LB48JJ",
    "tipo_entrega": "domicilio",
    "aplica_retiro": false,
    "motivo_no_aplica": "Este envío se entrega en el domicilio del destinatario, por lo que no requiere retiro en sucursal.",
    "sucursal_asignada": null,
    "sucursales_disponibles": [],
    "paquetes": []
  }
}
```

El token **es válido** — simplemente ese envío no se retira por sucursal. Devolver un `400` o un `404` haría que el frontend tuviera que distinguir "token inexistente" de "token válido pero a domicilio" leyendo el mensaje de error. Con este diseño, la pantalla solo mira `aplica_retiro` y muestra el `motivo_no_aplica` tal cual viene. Un token que realmente no existe sí devuelve `404 NOT_FOUND`.

### Por qué se listan también las otras sucursales de la ciudad

El paquete se entrega **únicamente** en la sucursal asignada al registrar el envío. Las otras sucursales de la misma ciudad se incluyen marcadas con `es_sucursal_asignada: false`, como referencia de la red cercana: el destinatario que no conoce la zona necesita ubicar "su" sucursal entre las que tiene alrededor, y la pantalla puede dibujarlas todas en el mapa destacando la correcta.

El filtro es por **provincia + ciudad** de la sucursal asignada, para no traer una sucursal homónima de otra provincia. La asignada siempre encabeza la lista, así el frontend no necesita ordenar ni buscar cuál destacar.

## La regla de dominio: cuándo decir que el paquete "ya se puede retirar"

Esta es la decisión de diseño más importante de la historia, y es una donde HU09 **se aparta a propósito** de HU13.

`ESTADOS_VALIDOS_PARA_RETIRO` (la lista que habilita el mostrador de HU13) incluye `"Pendiente"`. Eso tiene sentido ahí: cuando se implementó HU13 todavía no existía la recepción en terminal, así que los paquetes se quedaban en `"Pendiente"` para siempre y bloquear ese estado habría vuelto el mostrador inutilizable.

Pero reusar esa lista en la vista pública sería **engañoso**: le diría al destinatario "pasá a buscar tu paquete" cuando el paquete todavía está en manos del remitente, sin haber sido ni siquiera recibido en la terminal de origen. Por eso HU09 define su propia lista, más estricta:

```python
ESTADOS_YA_EN_SUCURSAL_DESTINO = {
    EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
    EstadoPaqueteEnum.EN_SUCURSAL.value,
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
}
```

`paquete_disponible_en_sucursal` usa solo esos tres estados: el paquete está físicamente en la sucursal de destino. Un paquete `"Pendiente"`, `EN_SUCURSAL_ORIGEN` o `EN_TRANSITO` aparece en la respuesta con `disponible_para_retirar: false`, y la pantalla puede mostrar "en camino" en vez de invitar al usuario a un viaje al vacío.

Las dos reglas viven en el mismo módulo ([`domain/rules/retiro_rules.py`](../../app/domain/rules/retiro_rules.py)) con la diferencia documentada en el docstring de la constante, justamente para que nadie las unifique por error creyendo que es una duplicación.

> Actualización (Sprint 2): `"Pendiente"` se quitó de `ESTADOS_VALIDOS_PARA_RETIRO` y ahora hay una sola lista para el mostrador de HU13 y la vista pública. Un paquete con retiro en sucursal que se recibe en su propia sucursal pasa directo a `LISTO_PARA_RETIRO` (HU06), así que ya no queda trabado en `"Pendiente"`.

## Privacidad de la vista pública

Como el endpoint no requiere autenticación, expone **solo** datos de logística: token, tipo de entrega, sucursales (que son información pública del catálogo), número/descripción/estado de los paquetes y los requisitos de retiro.

**No se exponen** email, teléfono ni documento del remitente o del destinatario. Mismo criterio que la vista pública de HU04 (ver [HU04](./hu04-seguimiento-publico.md)) y por la misma razón: cualquiera con el token —o que lo adivine— vería esos datos de contacto. Hay un test que verifica esto sobre el cuerpo crudo de la respuesta, no sobre campos concretos, para que agregar un campo nuevo al contrato no filtre un dato sensible sin que nadie se dé cuenta.

## Requisitos de retiro informados desde la vista pública

`requisitos_retiro` devuelve los mismos dos textos que HU13 exige en la ventanilla (titular: documento original y 16 años cumplidos; tercero: documento propio + copia del documento del titular + autorización firmada). La idea es que el destinatario no se entere de los requisitos recién cuando llega al mostrador y lo mandan de vuelta a su casa.

Hoy los textos están duplicados entre `contracts/sucursales.py:RequisitosRetiroPublico` (HU09) y `contracts/sucursal_retiro.py:RequisitosRetiroInfo` (HU13). Es una duplicación consciente y chica, pero **si esos textos cambian hay que cambiarlos en los dos lugares**; hay un test de HU09 que verifica su contenido, así que un cambio a medias se detecta. Si el equipo agrega más textos normativos, conviene mover todos a un módulo de dominio compartido.

## Estructura por capas

```text
api/v1/routers/sucursales.py                      # 2 endpoints públicos
application/services/servicio_sucursales.py       # catálogo + opciones de retiro
application/interfaces/servicio_sucursales.py     # IServicioSucursales
application/interfaces/repositorio_sucursales.py  # filtros en la firma de listar_todas
infrastructure/repositories/repositorio_sucursales.py  # filtros SQL case-insensitive
contracts/sucursales.py                           # SucursalRetiroData, OpcionesRetiroData, …
domain/rules/retiro_rules.py                      # reglas de HU09 junto a las de HU13
```

`ServicioSucursales` ahora recibe **dos** repositorios: `IRepositorioSucursales` (el catálogo) e `IRepositorioEnvios` (para resolver el token). Se reusó `IRepositorioEnvios.obtener_por_token`, que ya existía para HU04 y ya precarga `sucursal_destino` y `paquetes` — no hizo falta ninguna consulta nueva ni tocar ese repositorio.

## Cobertura de los criterios de aceptación

| Escenario de HU09 | Dónde se cumple | Test |
|:---|:---|:---|
| **Escenario 1** — DADO que el envío se gestiona para retiro y no a domicilio | `envio_habilita_retiro_en_sucursal` | `test_hu09_escenario_1_...`, `test_hu09_envio_a_domicilio_no_ofrece_sucursales` |
| **Escenario 1** — CUANDO el usuario consulta desde la experiencia pública | Ambos endpoints son públicos, sin `Depends` de autenticación | `test_hu09_no_requiere_autenticacion` |
| **Escenario 1** — ENTONCES el sistema muestra las sucursales disponibles para el retiro | `sucursal_asignada` + `sucursales_disponibles` | `test_hu09_escenario_1_muestra_las_sucursales_disponibles_para_retiro`, `test_hu09_lista_las_otras_sucursales_de_la_misma_ciudad` |

## Tests

[`tests/unit/test_retiro_rules.py`](../../tests/unit/test_retiro_rules.py) — se extendió el archivo existente de HU13 con las reglas de HU09: habilitación por `tipo_entrega` (incluida la normalización y los valores desconocidos) y la lista estricta de estados, con un test que documenta explícitamente por qué `"Pendiente"` **no** se anuncia como retirable aunque `evaluar_disponibilidad_retiro` lo acepte.

[`tests/integration/test_hu09_sucursales_retiro.py`](../../tests/integration/test_hu09_sucursales_retiro.py) — 14 casos: el escenario completo, el acceso sin autenticación, las sucursales de la misma ciudad (verificando que no se cuele una de otra ciudad), el estado por paquete, el caso a domicilio, el `404` por token inexistente, la no exposición de datos de contacto, los filtros del catálogo (por provincia, por ciudad, ambos, case-insensitive, sin coincidencias) y la compatibilidad del catálogo sin filtros.

El último test (`test_hu09_refleja_el_avance_del_paquete_tras_llegar_a_la_sucursal`) verifica la integración con el resto del ciclo: cuando el paquete pasa a estar en la sucursal de destino, la misma consulta pública empieza a anunciarlo como retirable.

## Lo que esta historia deja pendiente

- **El paquete todavía no puede llegar a `LISTO_PARA_RETIRO` por un flujo real.** HU06 lo deja en `EN_SUCURSAL_ORIGEN`; el salto a la sucursal de destino es el recorrido de larga distancia de HU10/HU11. Hasta entonces, `disponible_para_retirar` será `false` en cualquier envío creado por el flujo normal — el campo está correcto, es el flujo el que está incompleto.
- **No se avisa al destinatario cuando el paquete queda listo para retiro.** Sería el enganche natural de HU05 cuando exista la transición a `LISTO_PARA_RETIRO`.
- **El catálogo no informa horarios de atención** de cada sucursal: `SucursalModel` no tiene esa columna y el Product Backlog no la pide. Es el dato que más se va a extrañar en esta pantalla si el equipo decide ampliarla.
