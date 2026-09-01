# HU02 — Primer acceso y cambio obligatorio de contraseña

> Yo como Usuario Administrativo deseo realizar mi primer acceso con DNI y contraseña temporal y cambiar obligatoriamente la contraseña para comenzar a utilizar el sistema con contraseña propia.

No tiene un endpoint propio de "primer acceso": reutiliza `POST /api/v1/auth/login` (el mismo de HU01) y se diferencia por la respuesta, según el flag `requiere_cambio_password` del usuario.

## Escenario 1 — El login detecta que hace falta cambiar la clave

`ServicioAuth.autenticar_usuario` (`app/application/services/servicio_auth.py`), tras validar DNI y contraseña, revisa `usuario.requiere_cambio_password`. Si es `True`, en vez del login normal devuelve:

```json
{
  "status": "requires_password_change",
  "message": "Debe cambiar su contraseña temporal antes de continuar.",
  "data": {
    "temp_token": "eyJhbGciOi...",
    "requiere_cambio_password": true
  }
}
```

`temp_token` es un JWT con `scope=PASSWORD_RESET_ONLY` (ver [Autenticación y autorización](../03-seguridad/autenticacion-jwt.md)), vigente por `JWT_TEMP_TOKEN_EXPIRATION` (15 min por defecto). Con este token, cualquier endpoint protegido por `requerir_rol(...)` responde `403 FORBIDDEN_SCOPE` — el único camino habilitado es el cambio de contraseña.

## Escenario 2 y 3 — Cambio de contraseña

`POST /api/v1/auth/cambiar-password`, protegido por `Depends(validar_token_para_cambio_password)` (acepta tanto `temp_token` como un token pleno, para permitir también un cambio voluntario de clave).

Request:

```json
{
  "password_actual": "Tmp#9284Kz1!",
  "nueva_password": "MiNuevaPasswordSegura2026!",
  "confirmacion_password": "MiNuevaPasswordSegura2026!"
}
```

`ServicioAuth.cambiar_password` valida, en orden (y corta en el primer error, siempre con `400 PASSWORD_POLICY_ERROR`):

1. `nueva_password == confirmacion_password`.
2. La nueva contraseña cumple la política unificada (`domain/rules/password_rules.py:validar_politica_password` — ver [Autenticación y autorización](../03-seguridad/autenticacion-jwt.md)).
3. `password_actual` coincide con el hash almacenado del usuario (identificado por el `sub` del token, no por un campo del body — así nadie puede cambiar la clave de otro usuario aunque conozca su ID).

Si las tres pasan, actualiza el hash en base y pone `requiere_cambio_password=False` (`RepositorioUsuarios.actualizar_password`), y responde con un token nuevo de `scope=FULL_ACCESS`:

```json
{
  "status": "success",
  "message": "Contraseña actualizada exitosamente. Ya puede operar normalmente.",
  "data": { "auth_token": "eyJhbGciOi..." }
}
```

## Escenario 4 — Accesos posteriores

Con `requiere_cambio_password=False`, un login con DNI y la nueva contraseña sigue el camino normal de `ServicioAuth.autenticar_usuario` y devuelve directamente `status: "success"` con un token `FULL_ACCESS` — sin volver a pasar por el flujo de cambio obligatorio. La contraseña temporal anterior deja de ser válida porque su hash ya fue reemplazado en el paso anterior.

## Caso particular: el Superadministrador no pasa por HU02

El Superadministrador sembrado (`infrastructure/db/seed.py:sembrar_superadmin`) se crea con `requiere_cambio_password=False` desde el inicio — por diseño, HU02 aplica a los empleados dados de alta por HU01, no al Superadmin con credenciales precargadas (HU01, Escenario 1).

## Tests relevantes

`tests/integration/test_auth_flow.py::test_hu02_flujo_completo_primer_acceso_y_cambio_password` cubre los cuatro escenarios en una sola secuencia end-to-end (crear usuario con clave temporal → login detecta cambio obligatorio → rechazo por confirmación que no coincide → rechazo por clave débil → rechazo por clave actual incorrecta → cambio exitoso → login posterior con la clave nueva → la clave vieja ya no sirve). `tests/integration/test_security_scopes.py` cubre el bloqueo de endpoints administrativos con un token `PASSWORD_RESET_ONLY`.