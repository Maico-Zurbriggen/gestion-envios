# HU06 — Recepción de paquetes en terminal por escaneo del código de barras

> Yo como vendedor / personal de la terminal deseo escanear el código de barras de la planilla del envío al recibir el paquete, para identificar el paquete precargado y dejarlo listo en la terminal para su envío.

Prioridad: **Alta** · Estimación: **5 SP** · Contrato orientado a frontend: [`Back/Contrato/endpoints_frontend.md`, sección 9](../../Contrato/endpoints_frontend.md).

## Endpoints

| Método | Ruta | Autenticación | Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/terminal/paquetes/{codigo}/escanear` | Sí (Bearer JWT) | `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN` |
| `POST` | `/api/v1/terminal/paquetes/{codigo}/recepcionar` | Sí (Bearer JWT) | `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN` |

Router: [`app/api/v1/routers/recepcion_terminal.py`](../../app/api/v1/routers/recepcion_terminal.py).

## Por qué dos endpoints y no uno

El criterio de aceptación tiene dos verbos encadenados: *"el sistema **identifica** el paquete registrado y **permite dejarlo** registrado en la terminal"*. Eso se corresponde con dos momentos distintos del mostrador, y por eso son dos endpoints:

1. **Escanear** (`GET .../escanear`) es de **solo lectura**. El vendedor pasa el lector por la planilla y la pantalla le muestra qué paquete es, de quién viene, a dónde va y cuánto pesa, para contrastarlo con el bulto que tiene en el mostrador *antes* de asentar nada. Un escaneo no cambia el estado del paquete, así que escanear de más es inofensivo — algo importante cuando el disparador es un lector físico que puede emitir lecturas repetidas.
2. **Recepcionar** (`POST .../recepcionar`) es la **confirmación explícita** del vendedor, con la terminal donde quedó el bulto. Recién ahí el paquete cambia de estado.

Si fuera un solo endpoint, cada pasada del lector cambiaría el estado del paquete sin que nadie haya confirmado que el bulto físico se corresponde con la planilla.

## Qué código se escanea

La planilla imprimible de HU03 codifica el `numero_paquete` en un código de barras **CODE128** (componente `front/src/features/shipments/components/PackageBarcode.tsx`). Ese valor tiene el formato `PAQ-XXXXXXXXXX` (prefijo + 10 caracteres alfanuméricos en mayúsculas) que genera [`domain/rules/codigos_rules.py:generar_numero_paquete`](../../app/domain/rules/codigos_rules.py).

Las reglas de dominio de [`domain/rules/recepcion_rules.py`](../../app/domain/rules/recepcion_rules.py) **reusan las constantes de `codigos_rules`** (`PREFIJO_NUMERO_PAQUETE` y `LONGITUD_SUFIJO`) para armar la expresión regular de validación, en vez de repetir el formato: si algún día cambia la longitud del código generado, el validador acompaña el cambio solo.

### Normalización de lo que emite el lector

Un lector de código de barras no es un campo de texto prolijo: suele agregar un Enter final, puede intercalar espacios y algunos modelos emiten el texto en minúsculas. `normalizar_codigo_escaneado` elimina **todo** el espacio en blanco (incluido el interno) y pasa el valor a mayúsculas antes de buscar en la base:

```python
normalizar_codigo_escaneado("  paq-zpc5lb 48jj\n")  # -> "PAQ-ZPC5LB48JJ"
```

Sin esto, una lectura perfectamente válida devolvería `404` por un salto de línea invisible.

### También se acepta el UUID del paquete

El mismo endpoint resuelve el `id` (UUID) del paquete, además de su `numero_paquete`. Es para que el frontend pueda reusar los endpoints cuando ya tiene el identificador en memoria (por ejemplo, reintentar la recepción de un paquete que acaba de escanear) sin forzar al vendedor a volver a pasar el lector.

## La transición de estado

La recepción pasa el paquete de `"Pendiente"` a **`EN_SUCURSAL_ORIGEN`**, que es exactamente el "listo en la terminal para su envío" del criterio de aceptación: el paquete ya está en poder de la empresa, en una sucursal concreta, esperando ser despachado.

### Por qué se aceptan `"Pendiente"` y `"PENDIENTE"`

`ESTADOS_VALIDOS_PARA_RECEPCION` incluye las dos escrituras. HU03 persiste el literal `"Pendiente"` (ver `servicio_envios.py`), mientras que `EstadoPaqueteEnum` usa `PENDIENTE` en mayúsculas — el enum se incorporó al código recién con las historias de logística. Aceptar ambas evita que los envíos precargados antes de HU06 queden imposibles de recibir. **No se normalizó el valor histórico en una migración** porque eso tocaría datos de HU03 fuera del alcance de esta historia; la decisión queda registrada acá para que se resuelva de una vez cuando se unifique la máquina de estados completa (HU10-HU12).

### Estados que bloquean la recepción

`evaluar_disponibilidad_recepcion` devuelve `(disponible, motivo)` y distingue tres casos, porque el mensaje que necesita ver el vendedor es distinto en cada uno:

| Estado del paquete | ¿Se puede recibir? | Motivo que se informa |
|:---|:---:|:---|
| `Pendiente` / `PENDIENTE` | Sí | — |
| `EN_SUCURSAL_ORIGEN`, `EN_TRANSITO`, `EN_SUCURSAL_DESTINO`, `LISTO_PARA_RETIRO`, `EN_SUCURSAL`, `EN_REPARTO` | No | "El paquete ya fue recibido y está circulando en la red…" |
| `ENTREGADO`, `ENTREGADO_EN_SUCURSAL`, `RETIRADO` | No | "El paquete ya completó su ciclo de entrega…" |
| Cualquier otro | No | "El paquete no se encuentra en un estado que permita la recepción…" |

Esto es lo que hace que **un paquete no se pueda recibir dos veces**: el segundo `POST .../recepcionar` falla con `400 VALIDATION_ERROR` y el campo `estado` en `errors`.

## Asimetría deliberada: el escaneo no falla, la recepción sí

Un detalle de diseño que conviene no "corregir" por error más adelante:

- `GET .../escanear` de un paquete ya recibido responde **`200 OK`** con `disponible_para_recepcion: false` y el motivo. El vendedor escaneó algo que existe y necesita ver en pantalla qué pasó con ese bulto ("ya salió en tránsito el martes") — devolverle un error le ocultaría justamente la información que está buscando.
- `POST .../recepcionar` del mismo paquete responde **`400 VALIDATION_ERROR`**. Ahí sí hay una operación que no se puede ejecutar.

Mismo criterio que usa HU13 en su endpoint de validación de retiro.

## El campo `destino` y una corrección que salpicó a HU04

La pantalla del vendedor muestra el destino del envío en un solo renglón, igual que la vista pública de HU04. Al escribir HU06 se replicó esa lógica y el round-trip contra la API destapó un bug que ya existía:

```text
"Sucursal Sucursal Rosario Sur - Bv. Oroño 2456, Rosario, Santa Fe"
```

El formato era `f"Sucursal {sucursal.nombre} - ..."`, y **todas las sucursales del catálogo ya se llaman "Sucursal …"** (`sembrar_sucursales`), así que el prefijo salía duplicado.

En vez de arrastrar el bug a un segundo lugar, el formato se extrajo a [`domain/rules/destino_rules.py`](../../app/domain/rules/destino_rules.py) (`formatear_destino_domicilio` / `formatear_destino_sucursal`), que ahora usan **los dos** servicios: `ServicioSeguimiento` (HU04) y `ServicioRecepcionTerminal` (HU06). El helper agrega el prefijo solo si el nombre no lo trae, y además omite las partes vacías en vez de imprimir `None` o dejar comas sueltas.

Esto corrige de paso el `destino` que devolvía `GET /api/v1/seguimiento/{token}`. El cambio es visible en la respuesta de HU04, pero sus tests seguían pasando sin tocarlos porque verificaban con `in` y no con igualdad.

## Trazabilidad: qué se escribe en la base

`ServicioRecepcionTerminal.recepcionar_paquete` escribe tres cosas **en un solo commit** (`RepositorioRecepciones.registrar_recepcion_paquete`):

1. `paquetes.estado` → `EN_SUCURSAL_ORIGEN`.
2. `paquetes.sucursal_actual_id` → la terminal informada. Es la primera vez en el ciclo de vida del paquete que esta columna se completa.
3. Una fila nueva en `historial_estados_paquete`, con `estado_anterior`, `estado_nuevo`, el `usuario_id` del vendedor, la `sucursal_id`, las **coordenadas de la terminal** (`latitud`/`longitud`, copiadas del catálogo de sucursales) y una `observacion` que combina el texto automático con lo que haya tipeado el vendedor.

El punto del commit único es que la lectura pública de HU04 (que usa los campos denormalizados de `paquetes`) y el historial de auditoría nunca queden desfasados: no existe un instante en el que el paquete figure recibido sin su fila de historial, ni al revés.

## Autorización: por qué tres roles y no solo `VENDEDOR`

La historia es del "vendedor / personal de la terminal", y `VENDEDOR` es el rol natural. Se habilitan además `ADMINISTRATIVO` y `SUPERADMIN` porque en las sucursales chicas la misma persona atiende el mostrador y hace tareas administrativas; restringir a `VENDEDOR` puro obligaría a crear un segundo usuario para la misma persona. `REPARTIDOR` **no** está habilitado: no opera el mostrador de recepción.

La lista vive en una constante del router (`ROLES_TERMINAL`) para que quede en un solo lugar y los dos endpoints no puedan divergir.

Como en el resto del backend, un token con scope `PASSWORD_RESET_ONLY` (primer acceso de HU02 sin completar) recibe `403 FORBIDDEN_SCOPE` antes de cualquier otra validación — ver [Autenticación JWT](../03-seguridad/autenticacion-jwt.md).

## Estructura por capas

```text
api/v1/routers/recepcion_terminal.py          # 2 endpoints, roles, documentación OpenAPI
application/services/servicio_recepcion_terminal.py   # caso de uso
application/interfaces/servicio_recepcion_terminal.py # IServicioRecepcionTerminal
application/interfaces/repositorio_recepciones.py     # IRepositorioRecepciones
infrastructure/repositories/repositorio_recepciones.py # SQLAlchemy
contracts/recepcion_terminal.py               # schemas Pydantic de request/response
domain/rules/recepcion_rules.py               # validación de código y estados (sin I/O)
```

Dos decisiones de wiring ([`api/dependencies.py`](../../app/api/dependencies.py)):

- `RepositorioRecepciones` es **propio de HU06** y no reusa `IRepositorioEntregas` (de HU12/HU13) aunque la búsqueda por código se parezca: son los dos extremos opuestos del ciclo logístico — uno registra el ingreso del paquete a la red y el otro su salida definitiva. Mantenerlos separados evita que un cambio en el retiro afecte la recepción.
- En cambio, la validación de la sucursal **sí reusa** `IRepositorioSucursales.obtener_por_id`, que ya existía para HU03: no hacía falta una consulta nueva.

## Cobertura de los criterios de aceptación

| Escenario de HU06 | Dónde se cumple | Test |
|:---|:---|:---|
| **Escenario 1** — el cliente presenta la planilla, el vendedor escanea y el sistema identifica el paquete registrado | `escanear_paquete` resuelve el `numero_paquete` del código de barras y devuelve paquete + envío | `test_hu06_escenario_1_escaneo_identifica_el_paquete_precargado` |
| **Escenario 1** — …y permite dejarlo registrado en la terminal como listo para su envío | `recepcionar_paquete` → estado `EN_SUCURSAL_ORIGEN` + `sucursal_actual_id` + historial | `test_hu06_escenario_1_recepcion_deja_el_paquete_listo_en_la_terminal` |

## Tests

[`tests/unit/test_destino_rules.py`](../../tests/unit/test_destino_rules.py) — 9 casos del formateador compartido de destino, incluido el que fija el no-duplicado del prefijo "Sucursal".

[`tests/unit/test_recepcion_rules.py`](../../tests/unit/test_recepcion_rules.py) — 37 casos de las reglas puras (contando los parametrizados): normalización de lo que emite el lector, reconocimiento del formato (incluido el rechazo de un token `ENV-`, que no es un paquete), y los estados que habilitan o bloquean la recepción. Un test verifica el formato contra 20 códigos realmente generados por `generar_numero_paquete`, en vez de contra un literal.

[`tests/integration/test_hu06_recepcion_terminal.py`](../../tests/integration/test_hu06_recepcion_terminal.py) — 15 casos contra la app completa: los dos escenarios del criterio de aceptación, la matriz de autorización (sin token, `REPARTIDOR`, scope restringido, `VENDEDOR`, `ADMINISTRATIVO`), la escritura del historial, el rechazo de una recepción duplicada, el rechazo de una sucursal inexistente (verificando además que el paquete **no** quedó modificado) y la verificación de que el nuevo estado se refleja en la consulta pública de HU04.

Para los tests de autorización se agregaron a [`tests/conftest.py`](../../tests/conftest.py) las fixtures `repartidor_usuario` / `repartidor_token`, siguiendo la convención de las ya existentes para administrativo y vendedor.

## Lo que esta historia deja pendiente

- **No se notifica al remitente ni al destinatario** que el paquete fue recibido en la terminal. El criterio de aceptación de HU06 no lo pide (la notificación del token es HU05, al registrar el envío). Si el equipo decide avisar cada cambio de estado, el enganche natural es el `BackgroundTasks` que ya usa `POST /envios` con `ServicioNotificaciones`.
- **La terminal se informa en el request, no se deduce del usuario.** No existe hoy una relación "usuario → sucursal donde trabaja" (`RepartidorModel` tiene `sucursal_base_id`, pero solo para repartidores). Mientras no exista, el frontend tiene que mandar `sucursal_id`; cuando se agregue, el campo podría pasar a ser opcional y defaultear a la sucursal del vendedor autenticado.
- **No hay transición de salida.** El paquete queda en `EN_SUCURSAL_ORIGEN` y no existe todavía el endpoint que lo despache a `EN_TRANSITO`: eso es HU10/HU11.
