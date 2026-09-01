import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { NotFoundPage } from '../pages/NotFoundPage'
import { authRoutes } from './AuthRoutes'
import { mainRoutes } from './MainRoutes'
import { ProtectedRoutes } from './ProtectedRoutes'

const router = createBrowserRouter([
  ...authRoutes,
  {
    element: <ProtectedRoutes />,
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
