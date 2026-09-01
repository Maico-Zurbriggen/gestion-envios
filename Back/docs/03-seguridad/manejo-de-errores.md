# Manejo estándar de errores

Todas las respuestas de error de la API, sin excepción, siguen el mismo esquema JSON:

```json
{
  "status": "error",
  "code": "VALIDATION_ERROR",
  "message": "Los datos proporcionados no son válidos.",
  "errors": [
    { "field": "peso_kg", "message": "El peso no puede superar los 25 kg." }
  ]
}
```

`errors` es opcional: solo aparece cuando el problema puede atribuirse a uno o más campos concretos del payload.

## Cómo se logra que sea siempre igual

Hay dos mecanismos que convergen en el mismo formato, registrados en `app/api/middleware.py:registrar_manejadores_excepciones`:

1. **Excepciones de negocio explícitas** (`app/core/exceptions.py`): cada caso de uso lanza una subclase de `AppException` con el `code` y `status_code` ya definidos (ver tabla abajo). El handler de `AppException` simplemente serializa `code`, `message` y `errors` tal cual.
2. **Errores no anticipados por la capa de negocio**, capturados por handlers genéricos:
   - `RequestValidationError` (falla la validación automática de Pydantic antes de llegar al servicio, por ejemplo un campo `EmailStr` mal formado): se traduce a `400 VALIDATION_ERROR`, extrayendo el nombre de campo de la ubicación del error (`loc`) y limpiando el prefijo técnico `"Value error, "` que agrega Pydantic en validadores custom.
   - `StarletteHTTPException` (errores HTTP crudos, por ejemplo una ruta inexistente): se mapea el `status_code` HTTP a un `code` razonable (401→`INVALID_TOKEN`, 403→`FORBIDDEN_ACCESS`, 404→`NOT_FOUND`, etc.).
   - `Exception` genérica (cualquier bug no previsto): se loguea completo con traceback (`logger.error(..., exc_info=True)`) y se responde `500 INTERNAL_ERROR` sin exponer detalles internos al cliente.

## Tabla de códigos

| `code` | HTTP | Excepción en `core/exceptions.py` | Cuándo se usa |
|---|---|---|---|
| `AUTH_FAILED` | 401 | `AuthFailedException` | DNI o contraseña incorrectos, o usuario inactivo, en el login. |
| `VALIDATION_ERROR` | 400 | `ValidationException` (o automático de Pydantic) | Payload con formato inválido o que incumple una regla de negocio (ej. dimensiones de paquete). |
| `DUPLICATE_ENTRY` | 409 | `DuplicateEntryException` | DNI o email ya registrados al dar de alta un empleado. |
| `PASSWORD_POLICY_ERROR` | 400 | `PasswordPolicyException` | La nueva contraseña no cumple la política, no coincide con la confirmación, o la contraseña actual es incorrecta. |
| `INVALID_TOKEN` | 401 | `InvalidTokenException` | Token ausente, expirado, mal formado, o que referencia un usuario inexistente. |
| `FORBIDDEN_SCOPE` | 403 | `ForbiddenScopeException` | El token es válido pero su `scope` no alcanza para la operación (ej. token `PASSWORD_RESET_ONLY` usado fuera del cambio de clave). |
| `FORBIDDEN_ACCESS` | 403 | `ForbiddenAccessException` | El usuario está autenticado pero no tiene el rol requerido, o su cuenta no está activa. |
| `NOT_FOUND` | 404 | `NotFoundException` | Recurso inexistente (ej. token de seguimiento que no corresponde a ningún envío). |
| `INTERNAL_ERROR` | 500 | `AppException` genérica | Fallas internas no atribuibles al cliente (ej. no se pudo generar un token único tras varios intentos). |

`domain/constants/error_codes.py:ErrorCodes` centraliza estas mismas constantes como strings, para que los handlers genéricos de `middleware.py` no tengan que repetir literales.

## Convención para quien agregue un endpoint nuevo

- Preferir lanzar una de las excepciones ya existentes en `core/exceptions.py` antes que devolver una respuesta manual — así se garantiza el formato uniforme sin lógica adicional en el router.
- Si hace falta un código de error nuevo, agregarlo primero a `ErrorCodes` y crear la subclase de `AppException` correspondiente, siguiendo el mismo patrón (mensaje por defecto + `code` + `status_code` fijos en el `__init__`).
- Nunca dejar que una excepción de infraestructura (SQLAlchemy, `httpx`, etc.) llegue sin capturar a un router — como mínimo, la atrapa el handler genérico de `Exception`, pero es preferible convertirla explícitamente a una `AppException` con un mensaje entendible.