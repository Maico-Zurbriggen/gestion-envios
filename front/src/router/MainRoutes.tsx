import type { RouteObject } from 'react-router-dom'
import App from '../App'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'

export const mainRoutes: RouteObject[] = [
  {
    index: true,
    element: <App />,
  },
  {
    path: '/unauthorized',
    element: <UnauthorizedPage />,
  },
]
