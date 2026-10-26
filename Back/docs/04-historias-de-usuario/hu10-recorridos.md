# HU10 — Generar recorridos automáticamente, visualizarlos y editarlos manualmente

> Yo como personal de logística / administración deseo generar recorridos automáticamente, visualizarlos y editarlos manualmente, para organizar la distribución de paquetes y detectar domicilios que queden fuera de un recorrido.

Prioridad: **Alta** · Estimación: **21 SP** · Contrato orientado a frontend: [`Back/Contrato/endpoints_frontend.md`, sección 13](../../Contrato/endpoints_frontend.md).

## Endpoints

Todos requieren Bearer JWT con rol `ADMINISTRATIVO` o `SUPERADMIN`.

| Método | Ruta | Escenario |
|:---|:---|:---|
| `GET` | `/api/v1/repartidores` | soporte (1, 4) |
| `GET` | `/api/v1/repartidores/{usuario_id}` | soporte |
| `PUT` | `/api/v1/repartidores/{usuario_id}/perfil` | soporte (1, 4) |
| `POST` | `/api/v1/recorridos/generar` | 1, 3, 4 |
| `GET` | `/api/v1/recorridos` | 2 |
| `GET` | `/api/v1/recorridos/{id}` | 2 |
| `PUT` | `/api/v1/recorridos/{id}/paquetes` | 2, 3 |
| `DELETE` | `/api/v1/recorridos/{id}/paquetes/{codigo}` | 2, 3 |
| `PATCH` | `/api/v1/recorridos/{id}/paquetes/{codigo}/ubicacion` | 2 |
| `POST` | `/api/v1/recorridos/{id}/optimizar` | 2 |
| `PATCH` | `/api/v1/recorridos/{id}/repartidor` | 2 |
| `POST` | `/api/v1/recorridos/{id}/iniciar` | puente a HU11 |
| `DELETE` | `/api/v1/recorridos/{id}` | 2, 3 |
| `GET` | `/api/v1/recorridos/alertas` | 3 |
| `PATCH` | `/api/v1/recorridos/alertas/{id}/resolver` | 3 |

Routers: [`recorridos.py`](../../app/api/v1/routers/recorridos.py) y [`repartidores.py`](../../app/api/v1/routers/repartidores.py).

## Requisito previo: perfiles de repartidor

HU01 crea usuarios con rol `REPARTIDOR`, pero no hay forma de saber desde qué sucursal salen ni si hacen corta o larga distancia, y sin eso no se puede repartir nada. Ese dato vive en `repartidores` (extensión 1 a 1 de `usuarios`), que no tenía endpoint. `PUT /repartidores/{usuario_id}/perfil` lo crea o actualiza (`sucursal_base_id`, `tipo_reparto` `CORTA`/`LARGA`, `activo`).

Un repartidor está **disponible** si tiene perfil, `activo = true` y su cuenta está `Activo`. No se puede cambiar la sucursal, el tipo ni desactivar a un repartidor con recorridos generados, en edición o en curso (`409`): esos recorridos quedarían inconsistentes.

## Qué paquetes entran en un recorrido

Un paquete es candidato cuando:

1. Está físicamente en la sucursal (`paquetes.sucursal_actual_id`).
2. Está en un estado listo para despacho: `EN_SUCURSAL_ORIGEN` (recibido en la terminal, HU06), `EN_SUCURSAL_DESTINO` (llegó a la ciudad destino, HU11) o `ENTREGA_FALLIDA` (vuelve para reintentar, HU12).
3. No está pendiente en otro recorrido activo (`GENERADO`, `EN_EDICION` o `EN_CURSO`). Un paquete nunca queda en dos recorridos a la vez: se valida en la aplicación, como preveía el plan de base de datos, porque depende del estado del recorrido padre.

`Pendiente` (registrado pero no recibido) no entra: el paquete todavía no está en poder de la empresa.

## Escenario 4: corta o larga distancia

El tipo se decide por la **sucursal de entrega**: la última sucursal de la red antes del destinatario.

- Retiro en sucursal: la sucursal elegida en HU03. Si es la actual, no hay nada que repartir; si es otra, `LARGA`.
- Domicilio: la sucursal que lo atiende (`recorrido_rules.elegir_sucursal_de_entrega`): la actual si está en la misma ciudad; si no, una de esa ciudad (la más cercana al domicilio); si la ciudad no tiene sucursal, la más cercana. Si es la actual, `CORTA`; si no, `LARGA` hasta esa sucursal, desde donde saldrá después en un recorrido corto.

**Por qué no alcanza con comparar la ciudad.** La primera versión decidía "misma ciudad ⇒ corta". Con un domicilio en una localidad sin sucursal (Villa Carlos Paz) eso hacía que el paquete rebotara: desde Córdoba era "otra ciudad" (larga hasta la sucursal más cercana… que era Córdoba). Decidir por la sucursal que atiende el destino elimina el ciclo; hay un test de integración para ese caso.

En un recorrido `CORTA` cada parada es un domicilio y el repartidor vuelve a la sucursal; en uno `LARGA` cada parada es una sucursal donde se dejan paquetes y el recorrido termina en la última.

## Escenario 1: el algoritmo de generación

Toda la lógica es pura y vive en [`domain/rules/recorrido_rules.py`](../../app/domain/rules/recorrido_rules.py); el servicio solo traduce paquetes a `ParadaPlanificable` y aplica el resultado. Cada factor que pide el criterio de aceptación tiene su pieza:

| Factor del criterio | Cómo se resuelve |
|:---|:---|
| **Sucursal de partida** | Es el origen de todo recorrido: el reparto barre las paradas por ángulo alrededor de ella y el orden de visita parte de ella. Sin coordenadas de la sucursal no se genera (`400`). |
| **Orientación de las calles** | Dentro de una ciudad no se viaja en línea recta: la distancia urbana es Manhattan sobre los ejes de la cuadrícula, rotada `orientacion_calles_grados` respecto del norte (`distancia_urbana_km`). Cambiar la orientación cambia qué paradas quedan "cerca" y por lo tanto el orden (hay un test unitario que lo demuestra). Entre ciudades se usa la distancia geodésica × 1,25 de sinuosidad. |
| **Optimización del tiempo** | Orden de visita por vecino más cercano y mejora 2-opt hasta que ningún intercambio acorte el recorrido. Se estima la duración: viaje a 25 km/h urbano u 80 km/h en ruta, más 5 min por domicilio o 15 por sucursal. |
| **Distribución aproximadamente equitativa según la cantidad de repartidores** | Las paradas se ordenan por ángulo alrededor de la sucursal empezando después del mayor hueco (barrido) y se parten en tramos contiguos minimizando la carga máxima de **paquetes** por repartidor (partición lineal por programación dinámica). Cada repartidor recibe una zona compacta y una carga pareja. Un test verifica la optimalidad contra fuerza bruta. |

Los paquetes con el mismo destino (mismo domicilio o misma sucursal) comparten parada y viajan juntos: el reparto pondera cada parada por su cantidad de paquetes.

**Por qué no un motor de ruteo externo.** Con un servicio como OSRM se podrían considerar los sentidos de circulación reales calle por calle, pero el proyecto decidió no tercerizar nada por ahora. La métrica está aislada en `funcion_distancia`: reemplazarla por una consulta a un motor de ruteo es un cambio local, el resto del algoritmo no se entera.

### Reglas de la generación

- Se genera por **sucursal + fecha + tipo**. La fecha por defecto es hoy.
- Si ya hay recorridos sin iniciar para esa combinación, `409` salvo `reemplazar_existentes: true`, que los descarta y vuelve a generar. Los recorridos en curso nunca se tocan, y sus paquetes no se reasignan.
- Por defecto se reparte entre todos los repartidores disponibles de la sucursal y el tipo que no tengan ya un recorrido activo ese día; con `repartidor_ids` se elige un subconjunto (cada uno se valida).
- Si hay más repartidores que paradas, los que sobran no reciben recorrido.
- La orientación usada y las estimaciones se guardan en el recorrido (ver migración), para que una edición posterior recalcule con la misma métrica.

## Escenario 2: visualización y edición manual

`GET /recorridos/{id}` devuelve el recorrido listo para un mapa: sucursal de origen con coordenadas, `paradas` en orden (tipo, destino legible, coordenadas, sucursal de destino si es larga distancia, paquetes con número, estado y **teléfono del destinatario**, que necesita el repartidor según HU12 Escenario 2), `trazado` (secuencia de puntos en orden de visita) y estimaciones.

La edición solo se permite en `GENERADO` o `EN_EDICION`:

- `PUT /{id}/paquetes`: la lista completa en el orden de visita. Agrega, quita y reordena en una sola operación. Cada paquete se valida (que exista, que esté en la sucursal de partida y listo, que no esté en otro recorrido activo y que necesite un recorrido de este tipo) y los errores se informan por posición (`paquetes[i]`).
- `DELETE /{id}/paquetes/{codigo}`: atajo para quitar uno. No se puede quitar el último (para eso, eliminar el recorrido).
- `POST /{id}/optimizar`: recalcula el mejor orden de los paquetes actuales con la misma métrica (útil después de agregar paquetes a mano).
- `PATCH /{id}/repartidor`: reasigna a otro repartidor disponible de la misma sucursal y tipo; `409` si ya tiene otro recorrido activo ese día.

Una edición manual pasa el recorrido a `EN_EDICION` y `generado_automaticamente = false`, y recalcula distancia y duración.

**Domicilios sin coordenadas.** HU03 permite registrar un domicilio sin marcarlo en el mapa. Esos paquetes no se pueden ubicar, así que la generación los deja afuera con alerta; pero logística sí puede agregarlos a mano a un recorrido: aparecen como parada sin coordenadas (`paquetes_sin_ubicacion`), suman su tiempo de atención a la estimación y no figuran en el `trazado`.

`PATCH /{id}/paquetes/{codigo}/ubicacion` completa ese domicilio con `{ "latitud", "longitud" }` finitas y dentro de sus rangos geográficos. Solo se admite en corta distancia sin iniciar, para un paquete del recorrido cuyo envío todavía no tenga coordenadas completas. El punto se guarda en `envios` y se recalculan las estimaciones de todos sus recorridos activos editables, conservando el orden y marcándolos `EN_EDICION`. Se rechaza si hay un recorrido afectado en curso o si la ubicación cambia el tipo de reparto que corresponde a un recorrido asignado. No requiere migración.

## Escenario 3: alertas de domicilios sin recorrido

Al terminar **cualquier** generación o edición (el "control" del criterio), `_sincronizar_alertas` deja una fila en `alertas_recorrido` por cada paquete de la sucursal que necesita un recorrido de ese tipo y no tiene ninguno, con un motivo:

| Motivo | Cuándo |
|:---|:---|
| `SIN_UBICACION_DESTINO` | El destino no tiene coordenadas. |
| `SIN_SUCURSAL_DESTINO` | No se encontró sucursal a la cual trasladar el paquete. |
| `SIN_REPARTIDOR_DISPONIBLE` | No hay repartidores disponibles para ese tipo en la sucursal. |
| `SIN_RECORRIDO_ASIGNADO` | Quedó afuera tras una edición manual o al eliminar un recorrido. |

La sincronización es idempotente: no duplica alertas entre generaciones, actualiza el motivo si cambió, y **resuelve** sola (`resuelta`, `resuelta_at`) la alerta de un paquete que ya entró en un recorrido o dejó de necesitarlo. Las alertas del otro tipo de reparto no se tocan. Además se pueden resolver a mano (`PATCH /recorridos/alertas/{id}/resolver`) cuando se atendieron por fuera del sistema; si el paquete sigue sin recorrido, la próxima generación o edición la vuelve a crear.

Las respuestas de generar, editar y eliminar traen las alertas resultantes, así el aviso aparece en el momento en que termina el control.

`alertas_recorrido.motivo` no tiene `CHECK` constraint, por lo que los motivos nuevos (`MotivoAlertaRecorridoEnum`) no requirieron migración.

## Inicio del recorrido: el puente con HU11

HU10 termina cuando el recorrido está listo; HU11 es el repartidor ejecutándolo. `POST /{id}/iniciar` es la bisagra: en un solo commit pasa el recorrido a `EN_CURSO` y cada paquete a `EN_REPARTO` (corta) o `EN_TRANSITO` (larga), le quita la ubicación en sucursal (ya salió), agrega su fila en `historial_estados_paquete` (quién lo despachó, desde qué sucursal y con qué repartidor) y resuelve sus alertas. Es exactamente la transición que el [plan de base de datos](../01-arquitectura/plan-base-de-datos-completo.md) asignaba a HU10, y es lo que hace que el seguimiento público (HU04) muestre que el paquete salió. Antes de iniciar se verifica que cada paquete siga en la sucursal y listo (por ejemplo, que no se haya retirado en el mostrador mientras tanto).

Desde `EN_CURSO` el recorrido no se edita, no se reinicia y no se elimina. `FINALIZADO` queda para HU11/HU12.

## Cambios de esquema

Migración [`b7d41e9a2c63`](../../app/infrastructure/db/migrations/versions/b7d41e9a2c63_hu10_estimaciones_y_orientacion_de_recorridos.py):

- `recorridos.orientacion_calles_grados` (`FLOAT NOT NULL DEFAULT 0`), `distancia_estimada_km` y `duracion_estimada_min`.
- Índice `idx_recorrido_paquetes_paquete` sobre `recorrido_paquetes(paquete_id)`, previsto en la sección 5 del plan y ahora usado para saber si un paquete ya está en un recorrido.

Usa `batch_alter_table` para correr también sobre SQLite. Probada `upgrade` / `downgrade` / `upgrade` y `alembic check` sin diferencias. Ver en [Desarrollo local](../02-configuracion/desarrollo-local.md) qué hacer con una base local creada antes de esta migración.

Al probarla apareció un bug previo en la migración inicial: `historial_estados_paquete.id` se creaba como `BIGINT PRIMARY KEY`, que en SQLite no autoincrementa, así que una base creada con Alembic rechazaba todo insert de historial (HU06, HU13 y ahora HU10). Se corrigió usando la misma variante que el modelo; el DDL de PostgreSQL no cambia.

## Estructura por capas

```text
api/v1/routers/recorridos.py, repartidores.py
application/services/servicio_recorridos.py, servicio_repartidores.py
application/interfaces/servicio_recorridos.py, repositorio_recorridos.py, servicio_repartidores.py, repositorio_repartidores.py
infrastructure/repositories/repositorio_recorridos.py, repositorio_repartidores.py
contracts/recorridos.py, repartidores.py
domain/rules/recorrido_rules.py          # todo el algoritmo, sin I/O
domain/constants/estados_logistica.py    # MotivoAlertaRecorridoEnum
```

`IRepositorioRecorridos` expone, además de consultas, operaciones de unidad de trabajo (`agregar`, `eliminar`, `sincronizar`, `confirmar`): generar escribe en `recorridos`, `recorrido_paquetes` y `alertas_recorrido` y tiene que hacerlo en un solo commit. Al reemplazar los paquetes de un recorrido se borran las filas viejas con un `flush` previo, porque SQLAlchemy ordena los `INSERT` antes que los `DELETE` del mismo mapper y chocarían con las restricciones únicas `(recorrido, orden)` y `(recorrido, paquete)`.

## Cobertura de los criterios de aceptación

| Escenario de HU10 | Dónde se cumple | Tests |
|:---|:---|:---|
| **1** — generación considerando sucursal de partida, orientación de calles, tiempo y distribución equitativa | `generar` + `recorrido_rules` | `test_hu10_escenario_1_generacion_equitativa_por_zonas`, `test_hu10_escenario_1_orden_de_visita_optimizado`, unitarios de reparto, orientación y 2-opt |
| **2** — visualizar y editar manualmente | `obtener`, `reemplazar_paquetes`, `quitar_paquete`, `optimizar`, `reasignar_repartidor` | `test_hu10_escenario_2_visualizar_y_listar`, `test_hu10_escenario_2_edicion_manual_reordena_quita_y_alerta` y otros |
| **3** — alerta por domicilio sin recorrido al finalizar la generación o el control | `_sincronizar_alertas` | `test_hu10_escenario_3_alerta_por_domicilio_sin_ubicacion`, `test_hu10_escenario_3_alerta_sin_repartidores_y_se_resuelve_al_regenerar` |
| **4** — corta distancia en la ciudad, larga distancia entre ciudades dejando paquetes en sucursales | `determinar_tipo_reparto`, `elegir_sucursal_de_entrega` | `test_hu10_escenario_4_corta_y_larga_distancia`, `test_hu10_domicilio_de_localidad_sin_sucursal_lo_reparte_la_mas_cercana` |

## Tests

- [`tests/unit/test_recorrido_rules.py`](../../tests/unit/test_recorrido_rules.py) — 41 casos del algoritmo: tipos de reparto, sucursal de entrega, distancias y orientación, partición óptima, barrido, 2-opt y estimaciones.
- [`tests/integration/test_hu10_recorridos.py`](../../tests/integration/test_hu10_recorridos.py) — 25 casos contra la app completa, los cuatro escenarios más regeneración, selección de repartidores, validaciones, edición, inicio (corta y larga), eliminación y alertas.
- [`tests/integration/test_hu10_repartidores.py`](../../tests/integration/test_hu10_repartidores.py) — 6 casos de los perfiles de repartidor.
- El flujo de punta a punta ([`test_flujo_punta_a_punta.py`](../../tests/integration/test_flujo_punta_a_punta.py)) genera, edita e inicia un recorrido sobre paquetes registrados y recibidos por HTTP.

## Lo que esta historia deja pendiente

- **HU11 y HU12**: la ubicación del repartidor, el paso automático a `EN_SUCURSAL_DESTINO` por proximidad, la entrega y el cierre del recorrido (`FINALIZADO`, `estado_en_recorrido`). Los recorridos `EN_CURSO` ya traen todo lo que la app móvil necesita.
- **Capacidad del vehículo**: el reparto equilibra cantidad de paquetes, no peso ni volumen. Si se necesita, el peso ya está en `paquetes.peso_kg` y la partición puede ponderar por él.
- **Orientación por ciudad**: hoy se indica en cada generación. Si cada sucursal tiene una cuadrícula fija, conviene guardarla en `sucursales` y usarla como valor por defecto.
- **Sentidos de circulación reales**: requieren un motor de ruteo (ver arriba).
