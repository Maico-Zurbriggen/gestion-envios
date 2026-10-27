import type { RouteObject } from 'react-router-dom'
import { DriverDeliveryRoute } from '../features/delivery/components/DriverDeliveryRoute'
import { TerminalRoute } from '../features/terminal/components/TerminalRoute'
import App from '../App'
import { HomePage } from '../features/home/pages/HomePage'
import { PickupPage } from '../features/pickup/pages/PickupPage'
import { RoutesRoute } from '../features/routes/components/RoutesRoute'
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
        element: <ProtectedRoutes allowedRoles={['ADMINISTRATIVO', 'SUPERADMIN']} />,
        children: [
          {
            path: '/sucursal/retiros',
            element: <PickupPage />,
          },
          {
            path: '/recorridos',
            element: <RoutesRoute />,
          },
        ],
      },
      {
        element: <ProtectedRoutes allowedRoles={['REPARTIDOR']} />,
        children: [{ path: '/reparto', element: <DriverDeliveryRoute /> }],
      },
      {
        element: <ProtectedRoutes allowedRoles={['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN']} />,
        children: [{ path: '/terminal/recepcion', element: <TerminalRoute /> }],
      },
      {
        path: '/unauthorized',
        element: <UnauthorizedPage />,
      },
    ],
  },
]
