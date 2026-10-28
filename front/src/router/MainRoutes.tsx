import { Navigate, type RouteObject } from 'react-router-dom'
import { DriverDeliveryRoute } from '../features/delivery/components/DriverDeliveryRoute'
import { TerminalRoute } from '../features/terminal/components/TerminalRoute'
import App from '../App'
import { HomePage } from '../features/home/pages/HomePage'
import { RoutesRoute } from '../features/routes/components/RoutesRoute'
import { monitorRoute } from '../features/monitor/monitorRoutes'
import { UnloadRoute } from '../features/unload/components/UnloadRoute'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { ProtectedRoutes } from './ProtectedRoutes'
import { EmailTemplatesRoute, PickupRoute, UsersRoute } from './LazyPages'

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
            path: '/admin/usuarios',
            element: <UsersRoute />,
          },
          {
            path: '/admin/usuarios/nuevo',
            element: <Navigate to="/admin/usuarios?nuevo=1" replace />,
          },
        ],
      },
      {
        element: <ProtectedRoutes allowedRoles={['ADMINISTRATIVO', 'SUPERADMIN']} />,
        children: [
          {
            path: '/sucursal/retiros',
            element: <PickupRoute />,
          },
          {
            path: '/recorridos',
            element: <RoutesRoute />,
          },
          {
            path: '/admin/correos',
            element: <EmailTemplatesRoute />,
          },
          monitorRoute,
        ],
      },
      {
        element: <ProtectedRoutes allowedRoles={['REPARTIDOR']} />,
        children: [{ path: '/reparto', element: <DriverDeliveryRoute /> }],
      },
      {
        element: <ProtectedRoutes allowedRoles={['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN']} />,
        children: [
          { path: '/terminal/recepcion', element: <TerminalRoute /> },
          { path: '/terminal/descarga', element: <UnloadRoute /> },
        ],
      },
      {
        path: '/unauthorized',
        element: <UnauthorizedPage />,
      },
    ],
  },
]
