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

`App.tsx` monta el layout privado principal. Este layout contiene la navegación lateral, el encabezado móvil y un `Outlet` para las secciones internas. La barra es fija en escritorio, se transforma en drawer desde 968 px y ocupa el viewport completo hasta 460 px.

La ruta `/` muestra el Home y es el destino predeterminado después del login para todos los roles. Los módulos, sus rutas y los roles permitidos se declaran una sola vez en `front/src/app/navigation.ts`; tanto el Home como la barra lateral consumen esa configuración para no mostrar accesos que el usuario no puede utilizar. La autorización efectiva sigue aplicándose también en el router.

## Responsabilidades del estado

TanStack Query administra el ciclo de vida de las operaciones remotas. Redux conserva únicamente información global necesaria entre rutas, comenzando por la sesión autenticada.

El cierre de sesión no llama al backend: limpia Redux, las consultas de TanStack Query y la persistencia local antes de redirigir al login.
