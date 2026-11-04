import { Navigate, type RouteObject } from 'react-router-dom'
import { DriverDeliveryRoute } from '../features/delivery/components/DriverDeliveryRoute'
import { TerminalRoute } from '../features/terminal/components/TerminalRoute'
import App from '../App'
import { HomePage } from '../features/home/pages/HomePage'
import { RoutesRoute } from '../features/routes/components/RoutesRoute'
import { monitorRoute } from '../features/monitor/monitorRoutes'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { ProtectedRoutes } from './ProtectedRoutes'
import { AdminBranchesRoute, ChooseBranchRoute, PickupRoute, UsersRoute } from './LazyPages'

export const mainRoutes: RouteObject[] = [
  { path: '/elegir-sucursal', element: <ChooseBranchRoute /> },
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
          {
            path: '/admin/sucursales',
            element: <AdminBranchesRoute />,
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
        ],
      },
      {
        path: '/unauthorized',
        element: <UnauthorizedPage />,
      },
    ],
  },
]
