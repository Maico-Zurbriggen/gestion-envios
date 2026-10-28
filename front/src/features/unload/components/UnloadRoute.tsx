import { lazy, Suspense } from 'react'
import { LoaderCircle } from 'lucide-react'

const UnloadControlPage = lazy(() => import('../pages/UnloadControlPage').then((m) => ({ default: m.UnloadControlPage })))

export function UnloadRoute() {
  return (
    <Suspense
      fallback={
        <p className="monitor-loading" role="status">
          <LoaderCircle className="loading-icon" size={20} aria-hidden="true" />
          Preparando el control de descarga…
        </p>
      }
    >
      <UnloadControlPage />
    </Suspense>
  )
}
