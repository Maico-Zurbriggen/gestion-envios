import { lazy, Suspense } from 'react'
import { PageLoading } from '../../../shared/components/PageLoading'
const DriverDeliveryPage = lazy(() => import('../pages/DriverDeliveryPage'))
export function DriverDeliveryRoute() {
  return <Suspense fallback={<PageLoading label="Cargando tu reparto…" />}><DriverDeliveryPage /></Suspense>
}
