# Arquitectura del frontend

## Tecnologías

- React y TypeScript sobre Vite.
- React Router para navegación.
- Redux Toolkit para estado global del cliente.
- TanStack Query para consultas y mutaciones HTTP.

## Organización

La aplicación sigue una estructura por funcionalidad. Cada feature puede contener:

- `pages/`: vistas enlazadas desde el router.
- `hooks/`: coordinación entre UI, servidor y estado.
- `services/`: acceso HTTP y persistencia local.
- `redux/`: estado global propio de la funcionalidad.
- `types/`: contratos de API y modelos internos.

Las rutas públicas se declaran en `AuthRoutes.tsx`, las privadas en `MainRoutes.tsx` y se componen en `AppRouter.tsx`. `ProtectedRoutes.tsx` valida sesión y roles.

## Responsabilidades del estado

TanStack Query administra el ciclo de vida de las operaciones remotas. Redux conserva únicamente información global necesaria entre rutas, comenzando por la sesión autenticada.
