# Administración de usuarios

## Alta de empleados

- Ruta del frontend: `/admin/usuarios/nuevo`.
- Acceso: únicamente rol `SUPERADMIN`.
- Endpoint: `POST /api/v1/admin/empleados`.
- Autorización: token Bearer de la sesión.

El formulario trabaja con nombres camelCase y el servicio HTTP transforma el cuerpo al contrato del backend: `nombre`, `dni`, `email`, `telefono` y `rol_id`.

La respuesta exitosa incluye una contraseña temporal. Se muestra una sola vez en el resultado del alta y se ofrece una acción para copiarla; nunca se almacena en Redux ni en almacenamiento local.

## Roles provisionales

Hasta que exista el endpoint de consulta de roles, las opciones asignables se encuentran aisladas en `front/src/features/users/constants/roles.ts`:

- `2`: ADMINISTRATIVO
- `3`: VENDEDOR
- `4`: REPARTIDOR

`SUPERADMIN` no se ofrece como opción. Cuando esté disponible el endpoint, esta constante debe reemplazarse por una consulta de TanStack Query.
