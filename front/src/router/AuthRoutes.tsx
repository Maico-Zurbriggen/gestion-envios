import type { RouteObject } from 'react-router-dom'
import { ChangePasswordPage } from '../features/auth/pages/ChangePasswordPage'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { CreateShipmentRoute } from '../features/shipments/components/CreateShipmentRoute'
import { BranchesPage } from '../features/shipments/pages/BranchesPage'
import { TrackingRoute } from '../features/tracking/components/TrackingRoute'

export const authRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/cambiar-password',
    element: <ChangePasswordPage />,
  },
  {
    path: '/envios/nuevo',
    element: <CreateShipmentRoute />,
  },
  {
    path: '/sucursales',
    element: <BranchesPage />,
  },
  {
    path: '/seguimiento',
    element: <TrackingRoute />,
  },
]
