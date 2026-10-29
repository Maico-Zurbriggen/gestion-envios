import { lazy, Suspense } from 'react'
import { PageLoading } from '../../../shared/components/PageLoading'

const DeliveryRoutesPage = lazy(() => import('../pages/DeliveryRoutesPage').then((module) => ({ default: module.DeliveryRoutesPage })))

export function RoutesRoute() {
  return <Suspense fallback={<PageLoading label="Preparando la planificación de recorridos…" />}><DeliveryRoutesPage /></Suspense>
}
