import { useLayoutEffect } from 'react'
import { createBrowserRouter, Outlet, RouterProvider, useLocation, useNavigationType } from 'react-router-dom'
import { NotFoundPage } from '../pages/NotFoundPage'
import { authRoutes } from './AuthRoutes'
import { mainRoutes } from './MainRoutes'
import { ProtectedRoutes } from './ProtectedRoutes'

// Cada pantalla nueva arranca arriba de todo. Es instantáneo a propósito: con el scroll suave
// de base.css la animación se cortaba al cambiar de sección y la pantalla quedaba a mitad.
// Al volver atrás (POP) no se fuerza: el navegador recupera la posición.
function RootLayout() {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()
  useLayoutEffect(() => {
    if (navigationType !== 'POP') window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, navigationType])
  return <Outlet />
}

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      ...authRoutes,
      {
        // Solo exige sesión: la sucursal la piden las secciones (y no la pantalla para elegirla).
        element: <ProtectedRoutes requireBranch={false} />,
        children: mainRoutes,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
