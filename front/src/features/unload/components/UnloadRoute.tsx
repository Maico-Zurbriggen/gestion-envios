import { lazy, Suspense } from 'react'
import { PageLoading } from '../../../shared/components/PageLoading'

const UnloadControlPage = lazy(() => import('../pages/UnloadControlPage').then((m) => ({ default: m.UnloadControlPage })))

export function UnloadRoute() {
  return (
    <Suspense fallback={<PageLoading label="Preparando la carga y descarga…" />}>
      <UnloadControlPage />
    </Suspense>
  )
}
