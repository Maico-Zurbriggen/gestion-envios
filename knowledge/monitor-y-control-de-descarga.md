# Monitor de envíos y control de descarga

## Monitor de envíos

Sección general del menú lateral (`/monitor`), para `ADMINISTRATIVO` y `SUPERADMIN`, con cuatro subsecciones:

| Subsección | Ruta | Contenido |
|---|---|---|
| Resumen | `/monitor` | «Ir a un paquete» (escribir o escanear), indicadores, paquetes por etapa, lo que requiere atención y la actividad del día. |
| Paquetes | `/monitor/paquetes` | Todos los paquetes, con pestañas por etapa: pendientes, en depósito, en camino, para retirar, entregados y visita fallida. |
| Incidencias | `/monitor/incidencias` | Visitas fallidas, faltantes en la descarga, sin recorrido y con reclamo. |
| Reclamos | `/monitor/reclamos` | Bandeja para revisar, responder y cerrar reclamos. |

**Trazabilidad.** Se abre tocando un paquete, desde «Ir a un paquete» o desde las pantallas operativas: `/monitor/trazabilidad/:paquete`. No ocupa un lugar en el menú; mientras está abierta, se marca «Paquetes».

**Rutas anteriores.** `/monitor/pendientes`, `/deposito`, `/en-camino`, `/para-retirar` y `/entregados` redirigen a Paquetes con la pestaña correspondiente.

### Pantallas de listado

Paquetes e Incidencias comparten la misma organización:

- **Encabezado:** ícono, título y descripción.
- **Pestañas:** por etapa o por tipo de incidencia.
- **Panel de filtros plegable y fijo:** búsqueda, sucursal, tipo de entrega, fechas y orden, con un resumen de lo aplicado.
- **Listado en filas:** con paginado y exportación a CSV, que se abre con Excel.
- **Enlaces «Ver también»:** al pie.

Los filtros y la pestaña quedan en la URL, así que una búsqueda se puede compartir y el botón «Atrás» la conserva.

### Trazabilidad

Para cada paquete muestra:

- **Etapas:** las del paquete, con alertas destacadas si tuvo una visita fallida, faltó en la descarga, no tiene recorrido o tiene un reclamo.
- **Línea de tiempo filtrable**, con quién hizo cada movimiento y dónde:
  - registro del envío;
  - cambios de estado;
  - asignación a recorridos;
  - lecturas del control de descarga;
  - entregas y visitas fallidas, con la firma;
  - alertas, reclamos y avisos al cliente.
- **Datos del envío:** remitente y destinatario, destino con mapa, y los otros paquetes del mismo envío.
- **Acciones:** reimprimir la etiqueta.

Las pantallas operativas (Recibir paquetes, Registrar retiro, alertas y paradas de Recorridos) ofrecen el acceso «Ver trazabilidad» a quien puede entrar al monitor (`TraceLink`).

### API

Todas con prefijo `/api/v1/admin/monitor`.

| Endpoint | Uso |
|---|---|
| `GET /resumen` | Paquetes por etapa y por estado, especiales, actividad del día (desde las 00:00 en hora argentina), recorridos de hoy y sucursales. |
| `GET /paquetes` | Listado paginado (`por_pagina` ≤ 100). Acepta los parámetros de filtro de abajo. |
| `GET /paquetes/exportar` | Mismo filtro que el listado, en CSV separado por `;` con BOM (hasta 5000 filas). |
| `GET /paquetes/{numero}` | Trazabilidad completa. |
| `GET /entregas/{evento_id}/firma` | Imagen de la firma. |

Parámetros de filtro de `GET /paquetes` (y de la exportación):

- `buscar`
- `grupo`: un grupo de estados (`PENDIENTES`, `EN_DEPOSITO`, `EN_CAMINO`, `PARA_RETIRAR`, `NO_ENTREGADOS`, `ENTREGADOS`) o un filtro especial (`CON_PROBLEMAS`, `SIN_RECORRIDO`, `CON_RECLAMO`, `FALTANTES`)
- `sucursal_id`
- `tipo_entrega`
- `desde`, `hasta`
- `orden`

Las fechas sin zona horaria que devuelve SQLite se interpretan como UTC en el frontend (`parseApiDate`).

## Control de descarga en la sucursal de destino

Ruta: `/terminal/descarga`, módulo «Control de descarga» de Operación. Acceso: `VENDEDOR`, `ADMINISTRATIVO` y `SUPERADMIN`, el mismo personal que recibe paquetes en la terminal.

### Flujo

1. **Elegir la sucursal.** Se recuerda en el equipo con la misma clave que Recibir paquetes (`terminal-branch`).
2. **Elegir el recorrido.** Se listan los de larga distancia de los últimos 7 días que ya salieron (en curso o finalizados) y dejan paquetes en esa sucursal.
3. **Iniciar el control.** Es uno por recorrido y sucursal; si ya existe, se retoma.
4. **Escanear cada paquete que baja.** Con lector USB, o con la cámara del celular en modo continuo. Cada lectura da uno de estos resultados:
   - **Correcto:** tenía que bajar ahí. Si figuraba en tránsito, pasa a «En sucursal de destino» con historial a nombre de quien lo leyó, y su parada queda entregada. Cuando no quedan paradas pendientes, el recorrido se finaliza.
   - **Sobrante:** existe, pero no corresponde a esta descarga. Se explica si va a otra sucursal del mismo recorrido o si no viaja en él.
   - **Desconocido:** no existe un paquete con ese número.
   - **Lectura repetida:** un código leído dos veces no se cuenta de nuevo.
5. **Cerrar el control.** Cada paquete esperado que no se leyó genera una alerta `FALTANTE_EN_DESCARGA`. La alerta aparece en Incidencias → «Faltantes en la descarga», en la trazabilidad y en la bandeja de alertas de Recorridos. La sincronización automática de alertas al generar recorridos no la resuelve: la revisa una persona.

El GPS del repartidor de larga distancia sigue marcando la llegada por proximidad (10 km). El control de descarga confirma lo que llegó físicamente, y registra la llegada si el GPS no la marcó.

### API

Todas con prefijo `/api/v1/terminal/descargas`.

| Endpoint | Uso |
|---|---|
| `GET /recorridos?sucursal_id=` | Recorridos que llegan, con esperados, verificados y estado del control. |
| `POST /` | Iniciar o retomar el control (`recorrido_id`, `sucursal_id`). |
| `GET /{id}` | Esperados (verificados o no), sobrantes y resumen. |
| `POST /{id}/lecturas` | Registrar un código. |
| `POST /{id}/cerrar` | Cerrar el control con observaciones opcionales. |

### Persistencia

Tablas `controles_descarga` y `lecturas_descarga`, creadas por la migración `7f3c2a91d4b8`, que va después de `539e81c168e2`. El motivo de alerta nuevo no requiere migración, porque `alertas_recorrido.motivo` no tiene CHECK.
