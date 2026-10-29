# HU11 y HU12 — Ejecución del reparto y constancias de entrega

Implementación exclusivamente en `Back/`. Se reutilizan HU10 (recorridos,
paradas, orden, destinos e inicio), HU04 (seguimiento), HU05 (proveedor de
email y auditoría) y las tablas existentes de posiciones y eventos de entrega.
El aviso de visita fallida se envía por **email y WhatsApp** al destinatario (Product Backlog,
HU12 Escenario 3), con los proveedores de [Notificaciones](../02-configuracion/notificaciones-email-whatsapp.md).

## Endpoints privados

Todos requieren `Authorization: Bearer <token FULL_ACCESS>` de un usuario
`REPARTIDOR` activo, con perfil operativo activo. Solo permiten operar sobre
recorridos asignados a ese usuario y de su tipo de reparto. Un identificador
ajeno se responde como `404`, igual que uno inexistente. Las respuestas privadas
usan `Cache-Control: no-store`.

Base: `/api/v1/reparto/recorridos`.

| Método | Ruta relativa | Función y respuesta |
| --- | --- | --- |
| GET | `?fecha=AAAA-MM-DD&estado=EN_CURSO` | Mis recorridos; filtros opcionales. Mismo `ListarRecorridosResponse` de HU10. |
| GET | `/{id}` | `RecorridoResponse` de HU10: sucursal de origen, destinos, paradas y paquetes ordenados, contactos y trazado. |
| POST | `/{id}/iniciar` | Reutiliza el inicio de HU10: `EN_CURSO`, paquetes `EN_REPARTO` o `EN_TRANSITO`, con historial. |
| PUT | `/{id}/ubicacion` | Recibe coordenadas; devuelve la última posición. No cambia estados. |
| POST | `/{id}/llegadas` | Larga distancia: el repartidor marca la llegada a la próxima sucursal; actualiza los paquetes de esa parada y avisa los que quedan listos para retirar. |
| GET | `/{id}/ubicacion` | Última posición vinculada al recorrido; `data: null` si todavía no tiene una. |
| GET | `/{id}/paquetes/{codigo}/contacto` | Contacto del destinatario de un paquete a domicilio en un recorrido corto activo. |
| POST | `/{id}/paquetes/{codigo}/entrega` | Registra receptor, firma, fecha/hora, estado e historial en una transacción. |
| POST | `/{id}/paquetes/{codigo}/visita-fallida` | Registra intento, motivo, estado, historial y aviso pendiente en una transacción; luego despacha email. |
| GET | `/{id}/entregas/{evento_id}/firma` | PNG binario de una constancia de ese recorrido registrada por el usuario. `404` si no tiene firma. |

`codigo` acepta número de paquete o UUID. Las rutas administrativas existentes
de HU10 mantienen sus permisos y contratos.

### Actualizar posición

```json
{ "latitud": -31.41, "longitud": -64.19 }
```

```json
{
  "status": "success",
  "data": {
    "latitud": -31.41,
    "longitud": -64.19,
    "actualizado_at": "2026-10-26T13:00:00Z"
  }
}
```

Solo se acepta un recorrido `EN_CURSO`. Las coordenadas deben ser números
finitos en rangos `[-90, 90]` y `[-180, 180]`. No se aceptan campos adicionales.
La hora es la de recepción en el servidor, en UTC. Se conserva únicamente la
última posición del repartidor y el recorrido al que pertenece.

La posición **no modifica estados de paquetes**, ni en corta ni en larga
distancia: sirve para el mapa y para el seguimiento público.

### Llegada a una sucursal (larga distancia, HU11 Escenario 3)

```json
{ "sucursal_id": 4, "latitud": -34.58, "longitud": -58.42 }
```

El repartidor la marca desde la app con «Llegué a [sucursal]». Solo se acepta
en un recorrido `EN_CURSO` entre sucursales y para la **próxima** parada con
paquetes pendientes, en el mismo orden que muestra HU10; marcar otra devuelve
`400` con el nombre de la que corresponde. Cada paquete de esa parada queda:

- `LISTO_PARA_RETIRO`, con fecha límite de retiro, si se retira en esa sucursal;
- `EN_SUCURSAL_DESTINO`, si sigue a domicilio;
- en una devolución, listo para el remitente en su sucursal de origen, o
  `EN_DEVOLUCION` si todavía no llegó.

Se registra el historial a nombre del repartidor, con la sucursal y la posición
si se envió, y la asignación del tramo queda `ENTREGADO`. Los paquetes que
quedan listos para retirar generan el aviso al destinatario por email y
WhatsApp. Cuando todas las asignaciones se resolvieron, el recorrido queda
`FINALIZADO` y una nueva llegada o posición se rechaza con `400`.

### Constancia de entrega

```json
{
  "operacion_id": "95dcb24a-befc-49aa-8e74-d2cb35a0a400",
  "receptor_nombre": "María Gómez",
  "receptor_documento": "30111222",
  "receptor_fecha_nacimiento": "2000-01-01",
  "es_autorizado": false,
  "firma_base64": "<PNG codificado en base64, sin prefijo data:>"
}
```

El paquete debe ser de entrega a domicilio, estar `EN_REPARTO` y pendiente en
un recorrido corto activo. `es_autorizado` indica que recibe una persona
autorizada en lugar del destinatario; debe enviarse como booleano JSON.

La fecha de nacimiento permite verificar que el receptor sea estrictamente
mayor de 16 años en la fecha UTC del servidor. Se rechazan fechas futuras y
edades de más de 120 años. El día del cumpleaños número 16 no cumple la
condición; al día siguiente sí. Esta declaración se conserva como evidencia.

Se acepta PNG RGB/RGBA de 8 bits sin entrelazado, hasta 1024×1024 píxeles y
256 KiB decodificados. Se validan base64, cabecera, dimensiones, CRC de los
chunks y datos comprimidos. No se aceptan SVG/HTML ni un MIME arbitrario. La
imagen queda en `eventos_entrega.firma_imagen` y el MIME se fija a `image/png`.

El backend registra la hora, el repartidor y, si existe una posición de ese
recorrido, sus coordenadas. Guarda la constancia, actualiza el paquete a
`ENTREGADO`, la asignación a `ENTREGADO` y agrega el historial en un solo commit.
La firma nunca se devuelve en el seguimiento público.

### Contacto

```json
{
  "status": "success",
  "data": {
    "paquete_id": "uuid",
    "destinatario_nombre": "María Gómez",
    "telefono": "+543564222222",
    "telefono_disponible": true
  }
}
```

El teléfono se obtiene del envío, sin duplicarlo en una tabla. Si falta o
solo contiene espacios, devuelve `telefono: null` y `telefono_disponible: false`.

### Visita fallida

```json
{
  "operacion_id": "d3a71f44-e194-44e2-ad87-6f1c786b4603",
  "motivo_fallo": "Persona no encontrada en el domicilio"
}
```

El motivo se recorta y debe tener entre 3 y 255 caracteres. Se aplican las
mismas validaciones de recorrido, domicilio y estado que en una entrega.
El paquete pasa a `ENTREGA_FALLIDA` y la asignación a `FALLIDO`. No se inventa
un regreso físico a la sucursal a partir del registro de una visita.

Entregas y visitas devuelven `{ "status": "success", "data": ... }`, donde
`data` contiene `evento_id`, `paquete_id`, `recorrido_id`, `resultado`,
`receptor_nombre`, `receptor_documento`, `es_autorizado`, `firma_disponible`,
`motivo_fallo` y `fecha_hora` UTC. Los campos de receptor son nulos en una visita
fallida. No se devuelve la imagen dentro del JSON.

### Idempotencia, transacciones y notificaciones

- El cliente genera un UUID `operacion_id` una vez y lo conserva en cada
  reintento de esa operación. Un reintento con los mismos datos devuelve la
  misma constancia, incluso cuando el recorrido ya terminó.
- Un UUID reutilizado con otros datos o para otro paquete responde `409`.
  Una segunda entrega/visita con otro UUID para una asignación ya procesada
  también responde `409`.
- Se serializan las escrituras por repartidor y recorrido con locks
  transaccionales compatibles con SQLite y PostgreSQL. La actualización del
  paquete es condicional al estado anterior; una escritura concurrente no
  crea dos transiciones.
- El aviso pendiente se guarda junto con la visita. Se reutilizan
  `ServicioNotificaciones`, el proveedor de email de HU05 y
  `notificaciones_envio`. La restricción por evento y canal evita avisos
  duplicados; una reserva atómica impide despacharlos simultáneamente.
- El email informa paquete, fecha/hora y enlace de seguimiento. No incluye
  firma, documento ni motivo libre. La tarea utiliza su propia sesión.
- Un email aceptado por el proveedor queda `ENVIADO`; un rechazo, excepción
  o falta de dirección queda `FALLIDO`. Un fallo de email no revierte la
  visita ni produce una respuesta falsa de email enviado.
- Repetir la misma operación reintenta un aviso `PENDIENTE` o `FALLIDO`, sin
  reenviar uno `ENVIADO` y sin duplicar la visita.
- Se conserva el patrón actual de tareas en segundo plano, sin cola externa.
  Si el proceso termina antes de iniciar la tarea, repetir la operación retoma
  el aviso pendiente. Si termina durante el despacho SMTP, la reserva
  `procesando_at` queda como operación incierta: requiere conciliación con el
  proveedor antes de liberarla para evitar un segundo envío. SMTP no ofrece
  garantía de entrega exactamente una vez ante una caída del proceso.

## Integración con seguimiento público

`GET /api/v1/seguimiento/{token}` conserva los campos anteriores y agrega,
en cada paquete:

- `historial`: eventos ordenados con `estado_anterior`, `estado`, `fecha_hora`
  y una `descripcion` pública. La visita fallida aparece como aviso de visita.
  No se publica el texto libre del operador ni datos de receptor o repartidor.
- `ubicacion_repartidor`: `{latitud, longitud, actualizado_at}` o `null`.
  Solo se expone para un paquete pendiente en un recorrido `EN_CURSO`, con
  perfil activo y última posición asociada a ese mismo recorrido. Deja de
  exponerse al resolver esa asignación o finalizar el recorrido. No expone
  identificadores internos del repartidor ni posiciones de otros recorridos.

Es una consulta por polling: no existía infraestructura de WebSocket/SSE y
no se incorporó una nueva para estas historias.

## Migración y puesta en funcionamiento

Revisión Alembic `d2a6f81112ac`, posterior a `b7d41e9a2c63`.
No crea tablas ni agrega dependencias.

En `eventos_entrega` agrega `operacion_id` único, `solicitud_hash`,
`recorrido_id` con FK y `receptor_fecha_nacimiento`. En `notificaciones_envio`
agrega `evento_entrega_id` con FK, `procesando_at` y unicidad por evento/canal.
Las columnas nuevas permiten nulos para conservar las constancias existentes
de HU13 y los avisos de HU05. Se usa `batch_alter_table` para SQLite.

Desde `Back/`, antes de ejecutar contra una base existente:

```powershell
& .\.venv\Scripts\python.exe -m alembic upgrade head
```

`create_all` no actualiza columnas de tablas existentes. La migración se
verificó en bases temporales; no se modificó la base de desarrollo del usuario.

Se usa la configuración actual de HU05 (`EMAIL_PROVIDER`, `SMTP_*` y
`FRONTEND_BASE_URL`), sin modificar `.env`. Las pruebas de correo utilizan
proveedores simulados; un despacho SMTP real necesita la configuración del
entorno y no se verificó contra un servidor externo.

## Archivos de la implementación

Creado:

- `app/api/v1/routers/reparto.py`
- `app/application/interfaces/servicio_reparto.py`
- `app/application/services/servicio_reparto.py`
- `app/contracts/reparto.py`
- `app/domain/rules/reparto_rules.py`
- `app/infrastructure/db/migrations/versions/d2a6f81112ac_hu11_hu12_reparto_y_constancias.py`
- `tests/unit/test_reparto_rules.py`
- `tests/integration/test_hu11_hu12_reparto.py`
- `tests/integration/test_hu11_hu12_concurrencia.py`
- `tests/integration/test_hu11_hu12_migracion.py`
- `docs/04-historias-de-usuario/hu11-hu12-reparto.md`

Modificado:

- `app/api/dependencies.py`
- `app/api/main.py`
- `app/application/interfaces/repositorio_entregas.py`
- `app/application/interfaces/repositorio_notificaciones.py`
- `app/application/interfaces/repositorio_recorridos.py`
- `app/application/interfaces/servicio_notificaciones.py`
- `app/application/services/servicio_notificaciones.py`
- `app/application/services/servicio_seguimiento.py`
- `app/contracts/seguimiento.py`
- `app/infrastructure/db/models.py`
- `app/infrastructure/repositories/repositorio_entregas.py`
- `app/infrastructure/repositories/repositorio_envios.py`
- `app/infrastructure/repositories/repositorio_notificaciones.py`
- `app/infrastructure/repositories/repositorio_recorridos.py`
- `Contrato/endpoints_frontend.md`
- `docs/README.md`

El documento de requisitos `HU11yHU12.md`, que ya estaba sin seguimiento en Git
al comenzar, se conserva sin cambios.

## Verificación

Desde `Back/`:

```powershell
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m compileall -q app tests
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=tests/.tmp-hu11-suite
```

Las pruebas nuevas cubren las tres situaciones de HU11 y HU12, permisos y
scope, posición pública acotada al recorrido activo, firma y edad, contacto
ausente, idempotencia, errores de email y reintentos, rollback de constancias,
solicitudes simultáneas con sesiones independientes en SQLite en disco,
migración reversible con constancias previas y flujo completo por HTTP desde
HU03 hasta la entrega. La suite también ejecuta las historias anteriores y
las comprobaciones de arquitectura existentes.

Resultado verificado: **372 pruebas aprobadas** (312 existentes y 60 nuevas),
sin fallos. Cuatro advertencias de deprecación de Alembic corresponden a la
configuración existente de `prepend_sys_path` sin `path_separator` explícito.
`pip check`, `compileall`, generación de OpenAPI, Ruff sobre los archivos Python
nuevos y `git diff --check` finalizaron correctamente. Todos los archivos de
la implementación pertenecen a `Back/`; no se ejecutaron tareas del frontend.
