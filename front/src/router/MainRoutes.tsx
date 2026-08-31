import { Navigate, type RouteObject } from 'react-router-dom'
import App from '../App'
import { CreateUserPage } from '../features/users/pages/CreateUserPage'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { ProtectedRoutes } from './ProtectedRoutes'

export const mainRoutes: RouteObject[] = [
  {
    element: <App />,
    children: [
      {
        index: true,
        element: <Navigate to="/admin/usuarios/nuevo" replace />,
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
