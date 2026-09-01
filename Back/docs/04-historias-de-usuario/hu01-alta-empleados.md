# HU01 — Alta de empleados por Superadministrador

> Yo como Superadministrador deseo iniciar sesión y gestionar el alta de empleados administrativos para habilitar y mantener usuarios administrativos que puedan operar el sistema.

## Endpoint

`POST /api/v1/admin/empleados` — router `app/api/v1/routers/admin.py`, protegido con `Depends(requerir_rol(RolEnum.SUPERADMIN))` (ver [Autenticación y autorización](../03-seguridad/autenticacion-jwt.md)).

Request (`contracts/empleados.py:CrearEmpleadoRequest`):

```json
{
  "nombre": "Carlos Gómez",
  "dni": "35123456",
  "email": "carlos.gomez@empresa.com",
  "telefono": "+543564123456",
  "rol_id": 2
}
```

Response exitosa (`201 Created`):

```json
{
  "status": "success",
  "message": "Empleado creado correctamente.",
  "data": {
    "id": "c1f82b71-...",
    "nombre": "Carlos Gómez",
    "dni": "35123456",
    "email": "carlos.gomez@empresa.com",
    "telefono": "+543564123456",
    "estado": "Activo",
    "rol": "ADMINISTRATIVO",
    "password_temporal": "Tmp#9284Kz1a"
  }
}
```

`password_temporal` viaja **una sola vez**, en esta respuesta. El backend no la vuelve a exponer en ningún otro endpoint (ni siquiera hasheada) — solo persiste el hash BCrypt.

## Lógica del caso de uso (`ServicioEmpleados.crear_empleado`)

1. Valida que `rol_id` corresponda a un rol existente (`400 VALIDATION_ERROR` si no).
2. Valida unicidad de `dni` y `email` contra la tabla `usuarios`; si alguno ya existe, `409 DUPLICATE_ENTRY` con un `errors[]` que puede incluir ambos campos a la vez.
3. Genera la contraseña temporal con `domain/rules/password_rules.py:generar_password_temporal` (10-12 caracteres, con mayúscula/minúscula/número/símbolo, PRNG criptográfico) y su hash BCrypt.
4. Crea el `UsuarioModel` con `estado="Activo"` y `requiere_cambio_password=True` — esto es lo que dispara el flujo de HU02 en el primer login del empleado.

## Validaciones de formato (capa de contrato)

- `dni`: solo dígitos, longitud entre 6 y 20 caracteres.
- `email`: formato validado por `EmailStr` de Pydantic.
- `telefono`: expresión regular que admite `+`, dígitos, espacios y guiones, 6 a 30 caracteres.

Cualquier violación de estas reglas nunca llega al servicio: Pydantic la rechaza antes, y el handler de `RequestValidationError` la devuelve como `400 VALIDATION_ERROR` (ver [Manejo de errores](../03-seguridad/manejo-de-errores.md)).

## Qué no cubre esta implementación

- No hay endpoint para **listar** ni **editar** empleados existentes — el frontend usa una lista fija de roles asignables mientras tanto (ver `knowledge/user-management.md`).
- No hay endpoint de **login del Superadministrador** distinto al login general: usa el mismo `POST /auth/login` que cualquier usuario (ver [HU02](./hu02-primer-acceso.md)), diferenciándose únicamente por su rol y por no tener `requiere_cambio_password`.

## Tests relevantes

`tests/integration/test_admin_empleados.py` y `tests/integration/test_security_scopes.py` (para el rechazo de roles no-Superadmin).