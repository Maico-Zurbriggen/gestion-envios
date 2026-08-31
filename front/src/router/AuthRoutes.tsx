import type { RouteObject } from 'react-router-dom'
import { ChangePasswordPage } from '../features/auth/pages/ChangePasswordPage'
import { LoginPage } from '../features/auth/pages/LoginPage'

export const authRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/cambiar-password',
    element: <ChangePasswordPage />,
  },
]
