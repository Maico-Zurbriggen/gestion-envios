# Autenticación y autorización

## Emisión y verificación de JWT

`app/infrastructure/auth/jwt_handler.py:ManejadorJWT` centraliza la emisión (`emitir_token`) y verificación (`decodificar_token`) de tokens. Cada JWT incluye:

```json
{
  "sub": "<uuid del usuario>",
  "rol": "SUPERADMIN | ADMINISTRATIVO | VENDEDOR | REPARTIDOR",
  "scope": "FULL_ACCESS | PASSWORD_RESET_ONLY",
  "iat": 1234567890,
  "exp": 1234567890
}
```

La firma usa `JWT_SECRET`/`JWT_ALGORITHM` (ver [Variables de entorno](../02-configuracion/variables-de-entorno.md)). Un token expirado o con firma inválida hace que `decodificar_token` lance `InvalidTokenException` (401, código `INVALID_TOKEN`).

## Scopes: por qué existen dos tipos de token

`domain/constants/scopes.py:ScopeEnum` define dos alcances:

- **`FULL_ACCESS`**: token normal, emitido tras un login exitoso sin pendientes. Da acceso a cualquier endpoint protegido según el rol del usuario.
- **`PASSWORD_RESET_ONLY`**: token de vida corta (`JWT_TEMP_TOKEN_EXPIRATION`, 15 min por defecto) emitido cuando el login detecta `requiere_cambio_password=True` (HU02, Escenario 1). Con este scope, el usuario **solo** puede llamar a `POST /auth/cambiar-password`; cualquier otro endpoint protegido por `requerir_rol(...)` lo rechaza antes de llegar a validar el rol (`api/dependencies.py:requerir_rol`, primer chequeo del validador).

Esto evita que alguien con una contraseña temporal pueda operar el sistema sin haberla cambiado primero, sin necesidad de una columna de "sesión bloqueada" en la base de datos — el propio token lleva la restricción.

## Dependencias de FastAPI para proteger endpoints

Todas viven en `app/api/dependencies.py`:

- `obtener_token_payload`: extrae el header `Authorization: Bearer <token>` y lo decodifica. Si falta o es inválido, `InvalidTokenException` (401).
- `obtener_usuario_actual`: además de decodificar, busca al usuario en base y valida que `estado == "Activo"`. Pensada para endpoints que necesitan el usuario completo sin exigir un rol específico.
- `requerir_scope(scope)`: fábrica de dependencia que exige un scope exacto en el token. Usada, por ejemplo, si un endpoint debiera ser accesible *solo* durante el flujo de cambio de contraseña.
- `validar_token_para_cambio_password`: caso especial para `POST /auth/cambiar-password`, que acepta tanto `PASSWORD_RESET_ONLY` como `FULL_ACCESS` (un usuario con sesión plena también puede cambiar su contraseña voluntariamente).
- `requerir_rol(rol)`: fábrica de dependencia que exige, en este orden: (1) que el scope no sea `PASSWORD_RESET_ONLY`, (2) que el usuario exista y esté activo, (3) que su rol coincida exactamente con `rol`. Es la que protege `POST /admin/empleados` exigiendo `RolEnum.SUPERADMIN`.

Los endpoints públicos (`POST /envios`, `GET /seguimiento/{token}`, `GET /sucursales`) no usan ninguna de estas dependencias — son accesibles sin token, por diseño de HU03/HU04.

## Hashing de contraseñas

`app/infrastructure/auth/hasher.py:HasherContrasenas` usa BCrypt (librería `bcrypt`) con costo configurable (`BCRYPT_SALT_ROUNDS`, default 12). Nunca se guarda ni se loguea una contraseña en texto plano; `verificar_password` compara contra el hash almacenado y devuelve `False` (no excepción) ante cualquier error de comparación, para no filtrar información por temporización o por excepción.

## Política de contraseñas

`app/domain/rules/password_rules.py` define una única política, reutilizada tanto para generar la contraseña temporal del alta de empleados (HU01) como para validar la nueva contraseña en el cambio obligatorio (HU02):

- Longitud: entre 10 y 12 caracteres para las generadas automáticamente; mínimo 10 para las elegidas por el usuario.
- Al menos una mayúscula, una minúscula, un dígito y un símbolo especial (`! @ # $ % & *`).
- Generación con `secrets` (PRNG criptográfico), nunca con `random`.

## Roles

`domain/constants/roles.py` define los 4 roles del sistema con IDs fijos (`RolIdEnum`) usados en el seed, y sus nombres (`RolEnum`) usados para comparar contra el claim `rol`/la relación `usuario.rol.nombre`. Por ahora solo `SUPERADMIN` tiene un endpoint que lo exige explícitamente (`POST /admin/empleados`); `ADMINISTRATIVO`, `VENDEDOR` y `REPARTIDOR` están definidos para historias de usuario futuras (HU06, HU10-HU13) que todavía no tienen endpoints propios.