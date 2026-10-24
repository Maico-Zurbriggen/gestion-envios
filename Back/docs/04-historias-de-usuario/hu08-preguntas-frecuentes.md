# HU08 — Sección de preguntas frecuentes

> Yo como usuario público deseo consultar una sección de preguntas frecuentes, para resolver dudas habituales sin iniciar sesión ni contactar a un operador.

Prioridad: **Baja** · Estimación: **3 SP** · Contrato orientado a frontend: [`Back/Contrato/endpoints_frontend.md`, sección 12](../../Contrato/endpoints_frontend.md).

## Endpoints

| Método | Ruta | Autenticación | Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/preguntas-frecuentes` | No (público) | — |
| `GET` | `/api/v1/admin/preguntas-frecuentes` | Sí (Bearer JWT) | `ADMINISTRATIVO`, `SUPERADMIN` |
| `GET` | `/api/v1/admin/preguntas-frecuentes/{id}` | Sí | ídem |
| `POST` | `/api/v1/admin/preguntas-frecuentes` | Sí | ídem |
| `PATCH` | `/api/v1/admin/preguntas-frecuentes/{id}` | Sí | ídem |
| `DELETE` | `/api/v1/admin/preguntas-frecuentes/{id}` | Sí | ídem |

Router: [`app/api/v1/routers/preguntas_frecuentes.py`](../../app/api/v1/routers/preguntas_frecuentes.py).

## Por qué el contenido vive en la base

El [plan de base de datos](../01-arquitectura/plan-base-de-datos-completo.md#6-decisiones-tomadas) dejó decidido que las preguntas frecuentes van en la tabla `preguntas_frecuentes` y no hardcodeadas en el frontend: así se corrige una respuesta sin un despliegue. Esa decisión solo tiene sentido si hay forma de editar el contenido, por eso además del endpoint público del criterio de aceptación se implementó la administración (`/admin/preguntas-frecuentes`).

## `GET /preguntas-frecuentes` — la vista pública

Cubre el Escenario 1: devuelve el contenido sin exigir sesión. Solo muestra preguntas con `publicada = true`.

```json
{ "status": "success", "data": { "total": 13, "categorias": [ {"nombre": "Envíos", "cantidad": 4} ], "preguntas": [ ... ] } }
```

Decisiones de la respuesta:

- **Orden:** lo decide solo `orden` (con `id` de desempate). Las categorías aparecen en el orden de su primera pregunta, así quien administra controla también el orden de las secciones sin un campo extra.
- **`categorias` siempre completas:** aunque se filtre, se listan todas las categorías publicadas con su cantidad, para que el frontend dibuje los filtros sin una segunda consulta. `preguntas` y `total` sí respetan los filtros.
- **Sin categoría → "General":** la vista pública nunca recibe una categoría vacía (`preguntas_frecuentes_rules.categoria_visible`).
- **Sección vacía → `200`** con listas vacías, no `404`.

### Filtros que ignoran tildes

`?categoria=` y `?q=` comparan sin distinguir mayúsculas **ni tildes**: "envios" encuentra "Envíos", "DOCUMENTO retirar" encuentra "¿Qué necesito para retirar?" (cada palabra del término tiene que estar en la pregunta, la respuesta o la categoría, en cualquier orden).

Esto se resuelve en memoria con reglas puras ([`domain/rules/preguntas_frecuentes_rules.py`](../../app/domain/rules/preguntas_frecuentes_rules.py)) y no en SQL, a propósito: ignorar tildes en SQL requiere la extensión `unaccent` de PostgreSQL, que no existe en SQLite (desarrollo y tests). Con el volumen de una sección de preguntas frecuentes, filtrar unas decenas de filas en memoria es trivial y se comporta igual en los dos motores.

## Administración del contenido

- **Alta** (`POST`): `pregunta` (5–255), `respuesta` (10–5000), `categoria` opcional (máx. 80), `orden` (0–10000, default 0), `publicada` (default `true`).
- **Modificación parcial** (`PATCH`): solo cambia los campos enviados. Para quitar la categoría se manda `"categoria": null` explícitamente; omitirla la deja igual. Un body vacío, o `null` en un campo obligatorio, es `400`.
- **Baja** (`DELETE`). Para ocultar sin perder el contenido conviene `PATCH` con `publicada: false`.
- **Sin duplicados:** la misma pregunta no se puede cargar dos veces aunque difiera en tildes, mayúsculas, espacios o signos (`¿Cómo retiro mi paquete?` = `como retiro mi paquete`) → `409 DUPLICATE_ENTRY`. Reescribir una pregunta con su propio texto no cuenta como duplicado.
- **Categorías normalizadas:** `" Envíos  "` se guarda como `"Envíos"`, para no terminar con tres secciones casi iguales.

Solo `ADMINISTRATIVO` y `SUPERADMIN` editan contenido público.

## Contenido inicial

`seed.py:sembrar_preguntas_frecuentes` carga 13 preguntas en 6 categorías (Envíos, Seguimiento, Retiro en sucursal, Entregas a domicilio, Reclamos) al arrancar la app. Dos decisiones:

1. **Solo siembra si la tabla está vacía.** Las sucursales se siembran comparando por nombre, pero acá eso sería un error: si un administrador borra o reescribe una pregunta, re-sembrar por texto la volvería a crear en cada arranque.
2. **Las respuestas usan las constantes del dominio.** Los límites de peso y medidas salen de `paquete_rules` (`PESO_MAX_KG`, `DIMENSION_MAX_CM`, `SUMA_DIMENSIONES_MAX_CM`), así la respuesta no queda desactualizada si cambian las reglas de HU03. Hay un test que lo verifica contra la respuesta servida.

El contenido refleja el comportamiento real del sistema: requisitos de retiro de HU13, envío del token de HU05, reclamos de HU07, etc. La lista de contenidos prohibidos es genérica y remite a los términos y condiciones de HU03 (Escenario 5).

## Estructura por capas

```text
api/v1/routers/preguntas_frecuentes.py                 # router público + router de administración
application/services/servicio_preguntas_frecuentes.py
application/interfaces/servicio_preguntas_frecuentes.py
application/interfaces/repositorio_preguntas_frecuentes.py
infrastructure/repositories/repositorio_preguntas_frecuentes.py
contracts/preguntas_frecuentes.py
domain/rules/preguntas_frecuentes_rules.py             # normalización, búsqueda y duplicados (sin I/O)
infrastructure/db/seed.py                              # contenido inicial
```

Sin cambios de esquema: la tabla ya existía.

## Cobertura de los criterios de aceptación

| Escenario de HU08 | Dónde se cumple | Test |
|:---|:---|:---|
| **Escenario 1** — el usuario accede a la sección desde la experiencia pública y ve el contenido sin iniciar sesión | `listar_publicas` | `test_hu08_escenario_1_consulta_publica_sin_iniciar_sesion` |

## Tests

- [`tests/unit/test_preguntas_frecuentes_rules.py`](../../tests/unit/test_preguntas_frecuentes_rules.py) — 13 casos de normalización, búsqueda y duplicados.
- [`tests/integration/test_hu08_preguntas_frecuentes.py`](../../tests/integration/test_hu08_preguntas_frecuentes.py) — 15 casos: el escenario, ocultamiento de no publicadas, filtros, sección vacía, idempotencia de la siembra, contenido sembrado coherente con las reglas, autorización y CRUD completo con validaciones.
