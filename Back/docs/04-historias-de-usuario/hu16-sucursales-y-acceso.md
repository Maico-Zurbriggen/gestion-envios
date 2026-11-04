# HU16 — Sucursales y acceso por sucursal

> Yo como Superadministrador deseo administrar las sucursales y que cada usuario del personal trabaje solo en las suyas, para organizar la operación por sucursal y evitar que se opere sobre otra.

Sprint 2 · Prioridad: **Alta** · Estimación: **8 SP**. Detalle de roles y pantallas: [sucursales por usuario](../../../knowledge/sucursales-por-usuario.md).

## Criterios de aceptación

1. **Alta de sucursal.** El Superadministrador da de alta y edita sucursales con nombre, dirección y ubicación válidos; solo las activas se ofrecen al público ([HU09](./hu09-sucursales-retiro.md)).
2. **Usuarios con sucursal.** Todo usuario del personal tiene al menos una sucursal; el repartidor, una sola, que es su base de reparto.
3. **Sucursal activa.** Con más de una sucursal, después del login se elige en cuál trabajar, y se puede cambiar sin volver a iniciar sesión.
4. **Sucursal no habilitada.** Lo que corresponde a una sucursal no habilitada se rechaza en el servidor.

## Endpoints

| Método | Ruta | Roles |
|:---|:---|:---|
| `GET` | `/api/v1/admin/sucursales` | `SUPERADMIN` |
| `POST` | `/api/v1/admin/sucursales` | `SUPERADMIN` |
| `PUT` | `/api/v1/admin/sucursales/{id}` | `SUPERADMIN` |

Los usuarios con sus sucursales se administran en `/api/v1/admin/empleados` ([HU01](./hu01-alta-empleados.md)).

## Implementación

- **Ubicación:** la dirección se ubica con Georef ([`ubicacion.py`](../../app/infrastructure/mapas/ubicacion.py)). Las coordenadas son el punto de partida de los recorridos.
- **Sucursales por usuario:** tabla `usuario_sucursales` (migración `e5b19c3a7d20`). El Superadministrador entra en todas sin asignación.
- **Control en el servidor:** `sucursales_habilitadas`, `verificar_sucursal` (403) y `exigir_sucursal` (los listados piden la sucursal), en [`dependencies.py`](../../app/api/dependencies.py). Los aplican recepción, retiro, recorridos, repartidores, monitor y reclamos.

## Pruebas

[`tests/integration/test_sucursales.py`](../../tests/integration/test_sucursales.py), [`tests/integration/test_sucursales_por_usuario.py`](../../tests/integration/test_sucursales_por_usuario.py) y [`tests/integration/test_admin_usuarios.py`](../../tests/integration/test_admin_usuarios.py).
