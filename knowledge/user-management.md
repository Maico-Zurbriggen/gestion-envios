# Administración de usuarios

## Pantalla de usuarios

- Ruta del frontend: `/admin/usuarios` (módulo «Usuarios» del menú, sección Administración).
- `/admin/usuarios/nuevo` se conserva como enlace y redirige a `/admin/usuarios?nuevo=1`, que abre el alta.
- Acceso: únicamente rol `SUPERADMIN`, en el frontend y en el backend.

La pantalla reúne todo el ciclo del personal:

- Indicadores: total, activos, dados de baja y repartidores. El resumen se calcula sobre todo el personal, no sobre el filtro, así no cambia al buscar.
- Pestañas por estado con contador, filtro por rol y búsqueda por nombre, DNI, email o teléfono.
- Una fila por usuario con insignias de rol, estado, «Vos» y «Contraseña temporal» cuando todavía no la cambió.
- Acciones por fila: editar datos y rol, blanquear contraseña y dar de baja o reactivar. Las tres piden confirmación o se hacen en un modal.

## Endpoints

| Acción | Endpoint |
|---|---|
| Alta | `POST /api/v1/admin/empleados` |
| Listado con filtros | `GET /api/v1/admin/empleados?buscar&rol_id&estado` |
| Detalle | `GET /api/v1/admin/empleados/{id}` |
| Editar datos o rol | `PATCH /api/v1/admin/empleados/{id}` (solo los campos que cambian) |
| Baja o reactivación | `PATCH /api/v1/admin/empleados/{id}/estado` con `Activo` o `Inactivo` |
| Blanquear contraseña | `POST /api/v1/admin/empleados/{id}/restablecer-password` |

El frontend trabaja en camelCase y `usersApi.ts` traduce al contrato snake_case del backend.

## Reglas

- Nadie puede cambiar su propio rol, darse de baja ni blanquear su propia contraseña. Para la suya se usa «Cambiar mi contraseña».
- Siempre debe quedar al menos un `SUPERADMIN` activo: no se puede bajar ni cambiar de rol al último.
- DNI y email son únicos. El email se guarda en minúsculas.
- La baja no borra datos. El usuario dado de baja no puede ingresar, y la validación se hace en cada petición, así que la sesión que tenga abierta deja de funcionar.
- El blanqueo genera una contraseña temporal y obliga a cambiarla en el próximo ingreso.

## Contraseñas temporales

El alta y el blanqueo devuelven una contraseña temporal. Se muestra una sola vez en un modal con botón para copiarla. Nunca se guarda en Redux ni en el almacenamiento local.

## Roles asignables

Los roles se consultan con TanStack Query desde `GET /api/v1/roles` y se mantienen frescos durante cinco minutos. En el alta no se ofrece `SUPERADMIN` (HU01). Al editar sí se ofrece, para poder delegar la administración.
