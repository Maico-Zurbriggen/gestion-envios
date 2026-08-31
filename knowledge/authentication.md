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

El indicador `requiresPasswordChange` ya se conserva en el usuario. La ruta y el formulario de cambio obligatorio de contraseña quedan pendientes de definir junto con su endpoint.

Después de autenticar, el usuario vuelve a la ruta protegida que había solicitado o a `/` cuando no existe una ruta previa.
