# Administración de usuarios

## Alta de empleados

- Ruta del frontend: `/admin/usuarios/nuevo`.
- Acceso: únicamente rol `SUPERADMIN`.
- Endpoint: `POST /api/v1/admin/empleados`.
- Autorización: token Bearer de la sesión.

El formulario trabaja con nombres camelCase y el servicio HTTP transforma el cuerpo al contrato del backend: `nombre`, `dni`, `email`, `telefono` y `rol_id`.

La respuesta exitosa incluye una contraseña temporal. Se muestra una sola vez en el resultado del alta y se ofrece una acción para copiarla; nunca se almacena en Redux ni en almacenamiento local.

## Roles asignables

Las opciones se consultan con TanStack Query desde `GET /api/v1/roles`. El contrato remoto en snake_case se transforma a camelCase dentro del servicio y la consulta se mantiene fresca durante cinco minutos.

`SUPERADMIN` no se ofrece como opción en el alta de empleados aunque forme parte de la respuesta. Si la consulta falla, el formulario bloquea el envío y permite reintentar sin perder los datos ingresados.
