import type { RouteObject } from 'react-router-dom'
import App from '../App'
import { HomePage } from '../features/home/pages/HomePage'
import { CreateUserPage } from '../features/users/pages/CreateUserPage'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { ProtectedRoutes } from './ProtectedRoutes'

export const mainRoutes: RouteObject[] = [
  {
    element: <App />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        element: <ProtectedRoutes allowedRoles={['SUPERADMIN']} />,
        children: [
          {
            path: '/admin/usuarios/nuevo',
            element: <CreateUserPage />,
          },
        ],
      },
      {
        path: '/unauthorized',
        element: <UnauthorizedPage />,
      },
    ],
  },
]
