import { createBrowserRouter, Outlet, RouterProvider, ScrollRestoration } from 'react-router-dom'
import { NotFoundPage } from '../pages/NotFoundPage'
import { authRoutes } from './AuthRoutes'
import { mainRoutes } from './MainRoutes'
import { ProtectedRoutes } from './ProtectedRoutes'

// Cada pantalla nueva arranca arriba de todo; al volver atrás se recupera la posición.
function RootLayout() {
  return (
    <>
      <ScrollRestoration />
      <Outlet />
    </>
  )
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
