# Monitor de envíos

El circuito completo del paquete, con plazos y avisos, está en [circuito-logistico.md](./circuito-logistico.md).

Corresponde a HU15 (paquetes por etapa y trazabilidad) y HU17 (bandeja de reclamos). Sección general del menú lateral (`/monitor`), para `ADMINISTRATIVO` y `SUPERADMIN`. Muestra siempre la sucursal activa (ver [sucursales-por-usuario.md](./sucursales-por-usuario.md)). Tiene dos subsecciones:

| Subsección | Ruta | Contenido |
|---|---|---|
| Paquetes | `/monitor/paquetes` | Todos los paquetes de la sucursal, con pestañas por etapa: pendientes, en depósito, en camino, para retirar, entregados, visita fallida, devoluciones y vencidos. |
| Reclamos | `/monitor/reclamos` | Bandeja para revisar, responder y cerrar reclamos (HU17). |

- `/monitor` lleva a Paquetes.
- **Trazabilidad.** Se abre tocando un paquete o desde las pantallas operativas: `/monitor/trazabilidad/:paquete`. No ocupa un lugar en el menú; mientras está abierta, se marca «Paquetes».
- **Rutas anteriores.** `/monitor/pendientes`, `/deposito`, `/en-camino`, `/para-retirar` y `/entregados` redirigen a Paquetes con la pestaña correspondiente.

## Paquetes

- **Encabezado:** ícono, título, descripción y «Actualizar».
- **Pestañas por etapa:** cada una indica cuántos paquetes tiene.
- **Panel de filtros plegable:** búsqueda (paquete, código, persona o destino), tipo de entrega, fechas y orden, con un resumen de lo aplicado.
- **Listado en filas:** paginado.
- **Enlaces «Ver también»:** Recorridos y Reclamos.

Los filtros y la pestaña quedan en la URL, así que una búsqueda se puede compartir y el botón «Atrás» la conserva. El listado se refresca solo cada 30 segundos.

## Trazabilidad

Para cada paquete muestra:

- **Etapas:** las del paquete, con alertas destacadas si tuvo una visita fallida, no tiene recorrido, tiene un reclamo, vuelve al remitente o su registro venció.
- **Línea de tiempo filtrable**, con quién hizo cada movimiento y dónde:
  - registro del envío;
  - cambios de estado, incluida la llegada a cada sucursal (automática o marcada por el repartidor);
  - asignación a recorridos;
  - entregas y visitas fallidas, con la firma;
  - alertas, reclamos y avisos al cliente.
- **Datos del envío:** peso declarado y peso en balanza, sucursal de admisión, fecha límite de retiro, remitente y destinatario, destino con mapa, y los otros paquetes del mismo envío.
- **Acciones:** reimprimir la etiqueta.

Las pantallas operativas (Recibir paquetes, Registrar retiro, alertas y paradas de Recorridos) ofrecen el acceso «Ver trazabilidad» a quien puede entrar al monitor (`TraceLink`).

## API

Todas con prefijo `/api/v1/admin/monitor`.

| Endpoint | Uso |
|---|---|
| `GET /resumen?sucursal_id=` | Paquetes por etapa y por estado de la sucursal: alimenta los contadores de las pestañas. |
| `GET /paquetes` | Listado paginado (`por_pagina` ≤ 100). Acepta los parámetros de filtro de abajo. |
| `GET /paquetes/{numero}` | Trazabilidad completa. |
| `GET /entregas/{evento_id}/firma` | Imagen de la firma. |
| `POST /procesar-plazos` | Revisa los plazos en el momento. Los plazos se revisan solos cada 30 minutos (ver el circuito logístico). |

Parámetros de filtro de `GET /paquetes`:

- `sucursal_id`: obligatorio para quien no es Superadministrador.
- `buscar`.
- `grupo`: un grupo de estados (`PENDIENTES`, `EN_DEPOSITO`, `EN_CAMINO`, `PARA_RETIRAR`, `NO_ENTREGADOS`, `ENTREGADOS`, `DEVOLUCIONES`, `VENCIDOS`) o un filtro especial (`CON_PROBLEMAS`, `SIN_RECORRIDO`, `CON_RECLAMO`).
- `tipo_entrega`.
- `desde` y `hasta`.
- `orden`.

Las fechas sin zona horaria que devuelve SQLite se interpretan como UTC en el frontend (`parseApiDate`).
