import { lazy, Suspense } from 'react'
const DriverDeliveryPage = lazy(() => import('../pages/DriverDeliveryPage'))
export function DriverDeliveryRoute() {
  return <Suspense fallback={<p role="status">Cargando reparto…</p>}><DriverDeliveryPage /></Suspense>
}
