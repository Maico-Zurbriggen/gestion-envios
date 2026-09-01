import { lazy, Suspense } from 'react'
import { LoaderCircle } from 'lucide-react'

const CreateShipmentPage = lazy(() =>
  import('../pages/CreateShipmentPage').then((module) => ({
    default: module.CreateShipmentPage,
  })),
)

export function CreateShipmentRoute() {
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
            <h1>Preparando el formulario</h1>
            <p>Estamos cargando las herramientas para registrar tu envío.</p>
          </section>
        </main>
      }
    >
      <CreateShipmentPage />
    </Suspense>
  )
}
