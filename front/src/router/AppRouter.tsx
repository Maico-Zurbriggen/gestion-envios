import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { NotFoundPage } from '../pages/NotFoundPage'
import { authRoutes } from './AuthRoutes'
import { mainRoutes } from './MainRoutes'
import { ProtectedRoutes } from './ProtectedRoutes'

const router = createBrowserRouter([
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
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
