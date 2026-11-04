import { lazy, Suspense } from 'react'
import { LoaderCircle } from 'lucide-react'

const TrackingPage = lazy(() =>
  import('../pages/TrackingPage').then((module) => ({
    default: module.TrackingPage,
  })),
)

export function TrackingRoute() {
  return (
    <Suspense
      fallback={
        <main className="auth-bootstrap" aria-live="polite" aria-busy="true">
          <section className="auth-bootstrap__card auth-bootstrap__card--loading">
            <LoaderCircle
              className="auth-bootstrap__spinner auth-bootstrap__spinner--large"
              size={34}
              aria-hidden="true"
            />
            <h1>Consultando el recorrido</h1>
            <p>Estamos preparando el seguimiento de tu envío.</p>
          </section>
        </main>
      }
    >
      <TrackingPage />
    </Suspense>
  )
}
