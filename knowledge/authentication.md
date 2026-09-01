# Autenticación

## Login

- Base URL: variable `VITE_API_URL`.
- Endpoint: `POST /auth/login`.
- Cuerpo: `{ "dni": string, "password": string }`.
- La capa HTTP está aislada en `front/src/features/auth/services/authApi.ts` para poder ajustar el contrato sin modificar la vista.

La respuesta del backend se transforma a un modelo interno camelCase. En particular:

- `nombre` → `name`
- `rol` → `role`
- `requiere_cambio_password` → `requiresPasswordChange`

Los errores con `detail[]` se convierten en un mensaje visible en el formulario. También se contemplan respuestas no JSON, fallas de red y errores del servidor.

## Sesión

Redux conserva el token y el usuario autenticado. La sesión se persiste en `localStorage` para sobrevivir una recarga y `ProtectedRoutes` la utiliza para controlar acceso y roles.

Esta persistencia debe revisarse si el backend incorpora cookies HttpOnly y renovación de sesión, alternativa preferible para reducir la exposición del token a JavaScript.

El indicador `requiresPasswordChange` se conserva en el usuario y activa el flujo de cambio obligatorio cuando corresponde.

Después de autenticar, todos los usuarios ingresan siempre a `/`. No se restaura una ruta protegida anterior, porque podría pertenecer a otro rol o haber quedado guardada desde una sesión previa.

## Cambio obligatorio de contraseña

- Ruta del frontend: `/cambiar-password`.
- Endpoint real del backend: `POST /api/v1/auth/cambiar-password`.
- La llamada requiere `Authorization: Bearer <temp_token>`.
- Cuerpo: `{ "password_actual", "nueva_password", "confirmacion_password" }`.

Cuando el login responde `requires_password_change`, el token temporal y el DNI se guardan en `sessionStorage`; las contraseñas nunca se persisten. La vista queda inaccesible si no existe un token normal o un desafío temporal.

La contraseña nueva debe tener al menos 10 caracteres, mayúscula, minúscula, número y uno de los símbolos `! @ # $ % & *`. Estas reglas se muestran y validan en tiempo real, pero el backend conserva la validación definitiva.

Al finalizar, el backend devuelve un token con acceso completo. Si el login temporal no proporcionó un perfil, el frontend conserva un usuario mínimo a partir del DNI y los claims firmados del token hasta que exista un endpoint de perfil como `/me`.
