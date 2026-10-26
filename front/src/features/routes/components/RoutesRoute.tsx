import { lazy, Suspense } from 'react'
import { RouteLoading } from './RouteFeedback'

const DeliveryRoutesPage = lazy(() => import('../pages/DeliveryRoutesPage').then((module) => ({ default: module.DeliveryRoutesPage })))

export function RoutesRoute() {
  return <Suspense fallback={<RouteLoading label="Preparando la planificación de recorridos…" />}><DeliveryRoutesPage /></Suspense>
}
