import type { RouteObject } from 'react-router-dom'
import { ChangePasswordPage } from '../features/auth/pages/ChangePasswordPage'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { FaqPage } from '../features/faq/pages/FaqPage'
import { CreateShipmentRoute } from '../features/shipments/components/CreateShipmentRoute'
import { BranchesPage } from '../features/shipments/pages/BranchesPage'
import { TrackingRoute } from '../features/tracking/components/TrackingRoute'
import { PublicPageLayout } from '../layouts/PublicPageLayout'

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
      { path: '/sucursales', element: <BranchesPage /> },
      { path: '/preguntas-frecuentes', element: <FaqPage /> },
    ],
  },
]
