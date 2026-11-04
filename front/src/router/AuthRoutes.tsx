import type { RouteObject } from 'react-router-dom'
import { ChangePasswordPage } from '../features/auth/pages/ChangePasswordPage'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { CreateShipmentRoute } from '../features/shipments/components/CreateShipmentRoute'
import { TrackingRoute } from '../features/tracking/components/TrackingRoute'
import { PublicPageLayout } from '../layouts/PublicPageLayout'
import { BranchesRoute, FaqRoute } from './LazyPages'

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
    element: <PublicPageLayout />,
    children: [
      { path: '/envios/nuevo', element: <CreateShipmentRoute /> },
      { path: '/seguimiento', element: <TrackingRoute /> },
      { path: '/sucursales', element: <BranchesRoute /> },
      { path: '/preguntas-frecuentes', element: <FaqRoute /> },
    ],
  },
]
