# HU17 — Bandeja interna de reclamos

> Yo como personal de sucursal deseo revisar, responder y cerrar los reclamos de los envíos de mi sucursal, para resolver el inconveniente y que el cliente vea la respuesta.

Sprint 3 · Prioridad: **Media** · Estimación: **3 SP**. Continúa el inicio público de [HU07](./hu07-reclamos.md).

## Criterios de aceptación

1. **Respuesta a un reclamo.** El personal abre el reclamo en la bandeja, lo responde y lo cierra; la respuesta queda visible en el seguimiento público del envío.
2. **Reclamos de la sucursal.** La bandeja muestra solo los reclamos de los envíos que pasan por la sucursal activa ([HU16](./hu16-sucursales-y-acceso.md)).

## Endpoints

| Método | Ruta | Roles |
|:---|:---|:---|
| `GET` | `/api/v1/admin/reclamos` | `ADMINISTRATIVO`, `SUPERADMIN` |
| `GET` | `/api/v1/admin/reclamos/{id}` | `ADMINISTRATIVO`, `SUPERADMIN` |
| `PATCH` | `/api/v1/admin/reclamos/{id}/estado` | `ADMINISTRATIVO`, `SUPERADMIN` |

Router: [`reclamos.py`](../../app/api/v1/routers/reclamos.py). Cerrar un reclamo (`RESUELTO` o `RECHAZADO`) exige `resolucion`. En el frontend: Monitor › Reclamos ([monitor](../../../knowledge/monitor.md)).

## Pruebas

[`tests/integration/test_hu07_reclamos.py`](../../tests/integration/test_hu07_reclamos.py).
