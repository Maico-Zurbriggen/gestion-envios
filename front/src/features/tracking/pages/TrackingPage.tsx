import { useState, type FormEvent } from 'react'
import {
  ArrowLeft,
  Box,
  CalendarClock,
  Check,
  CircleAlert,
  Clock3,
  House,
  LoaderCircle,
  LogIn,
  MapPin,
  Moon,
  PackageCheck,
  PackagePlus,
  RefreshCw,
  Route,
  Search,
  Sun,
  Truck,
  Warehouse,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { selectIsAuthenticated } from '../../auth/redux/authSlice'
import { useTheme } from '../../../shared/hooks/useTheme'
import { useShipmentTracking } from '../hooks/useShipmentTracking'
import type { TrackedPackage } from '../types/tracking.types'
import './TrackingPage.css'

const TRACKING_STEPS = [
  { label: 'Registrado', description: 'Datos y etiqueta generados', icon: Check },
  { label: 'En sucursal', description: 'Recibido para despacho', icon: Warehouse },
  { label: 'En viaje', description: 'Traslado hacia el destino', icon: Truck },
  { label: 'Entregado', description: 'Recepción confirmada', icon: House },
] as const

function normalizeToken(value: string) {
  return value.toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 30)
}

function getStatusStep(status: string) {
  const normalizedStatus = status
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-AR')

  if (normalizedStatus.includes('entreg')) return 3
  if (
    normalizedStatus.includes('viaje') ||
    normalizedStatus.includes('transito') ||
    normalizedStatus.includes('camino') ||
    normalizedStatus.includes('reparto')
  ) {
    return 2
  }
  if (
    normalizedStatus.includes('sucursal') ||
    normalizedStatus.includes('admit') ||
    normalizedStatus.includes('recib')
  ) {
    return 1
  }
  return 0
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function PackageProgress({ shipmentPackage }: { shipmentPackage: TrackedPackage }) {
  const currentStep = getStatusStep(shipmentPackage.status)

  return (
    <article className="tracked-package">
      <header className="tracked-package__header">
        <span className="tracked-package__icon" aria-hidden="true">
          <Box size={22} />
        </span>
        <div>
          <span>Paquete</span>
          <h2>{shipmentPackage.packageNumber}</h2>
        </div>
        <span className="tracked-package__status">{shipmentPackage.status}</span>
      </header>

      <div className="tracked-package__content">
        <div className="tracked-package__description">
          <div>
            <span>Contenido declarado</span>
            <strong>{shipmentPackage.description}</strong>
          </div>
          {shipmentPackage.notes && (
            <div>
              <span>Observaciones</span>
              <strong>{shipmentPackage.notes}</strong>
            </div>
          )}
        </div>

        <ol className="tracking-timeline" aria-label="Progreso del paquete">
          {TRACKING_STEPS.map((step, index) => {
            const Icon = step.icon
            const state =
              index < currentStep
                ? 'is-complete'
                : index === currentStep
                  ? 'is-current'
                  : ''

            return (
              <li className={state} key={step.label}>
                <span className="tracking-timeline__point" aria-hidden="true">
                  <Icon size={17} />
                </span>
                <div>
                  <strong>{step.label}</strong>
                  <small>{step.description}</small>
                </div>
              </li>
            )
          })}
        </ol>

        <footer className="tracked-package__dates">
          <span>
            <CalendarClock size={15} aria-hidden="true" />
            Registrado {formatDate(shipmentPackage.registeredAt)}
          </span>
          <span>
            <RefreshCw size={15} aria-hidden="true" />
            Actualizado {formatDate(shipmentPackage.updatedAt)}
          </span>
        </footer>
      </div>
    </article>
  )
}

export function TrackingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialToken = normalizeToken(searchParams.get('token') ?? '')
  const [tokenInput, setTokenInput] = useState(initialToken)
  const [submittedToken, setSubmittedToken] = useState(initialToken)
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const { theme, toggleTheme } = useTheme()
  const trackingQuery = useShipmentTracking(submittedToken)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const token = normalizeToken(tokenInput.trim())
    if (!token) return

    if (token === submittedToken) {
      void trackingQuery.refetch()
      return
    }

    setSubmittedToken(token)
    setSearchParams({ token }, { replace: true })
  }

  const latestUpdate = trackingQuery.data?.packages.reduce<string | null>(
    (latest, shipmentPackage) =>
      !latest || new Date(shipmentPackage.updatedAt) > new Date(latest)
        ? shipmentPackage.updatedAt
        : latest,
    null,
  )

  return (
    <main className="tracking-page">
      <header className="tracking-public-header">
        <Link className="tracking-brand" to={isAuthenticated ? '/' : '/login'}>
          <span aria-hidden="true"><PackageCheck size={22} /></span>
          <strong>Gestión de envíos</strong>
        </Link>
        <div className="tracking-public-header__actions">
          <button type="button" onClick={toggleTheme} aria-label="Cambiar tema">
            {theme === 'light' ? <Moon size={19} aria-hidden="true" /> : <Sun size={19} aria-hidden="true" />}
          </button>
          <Link to={isAuthenticated ? '/' : '/login'} aria-label={isAuthenticated ? 'Volver al panel' : 'Iniciar sesión'}>
            {isAuthenticated ? <ArrowLeft size={18} aria-hidden="true" /> : <LogIn size={18} aria-hidden="true" />}
            <span>{isAuthenticated ? 'Volver al panel' : 'Ingresar'}</span>
          </Link>
        </div>
      </header>

      <div className="tracking-page__content">
        <section className="tracking-hero" aria-labelledby="tracking-title">
          <div>
            <span className="eyebrow"><Route size={15} aria-hidden="true" /> Seguimiento público</span>
            <h1 id="tracking-title">¿Dónde está tu paquete?</h1>
            <p>Ingresá el código de seguimiento del envío. No necesitás iniciar sesión.</p>
          </div>

          <form className="tracking-search" onSubmit={handleSubmit}>
            <label htmlFor="tracking-token">Código de seguimiento</label>
            <div>
              <input
                id="tracking-token"
                value={tokenInput}
                onChange={(event) => setTokenInput(normalizeToken(event.target.value))}
                placeholder="ENV-XXXXXXXXXX"
                autoComplete="off"
                spellCheck="false"
                minLength={5}
                required
                autoFocus
              />
              <button type="submit" disabled={trackingQuery.isFetching || !tokenInput.trim()}>
                {trackingQuery.isFetching ? <LoaderCircle className="loading-icon" size={19} aria-hidden="true" /> : <Search size={19} aria-hidden="true" />}
                {trackingQuery.isFetching ? 'Buscando…' : 'Buscar envío'}
              </button>
            </div>
          </form>
        </section>

        {trackingQuery.isError && (
          <section className="tracking-feedback tracking-feedback--error" role="alert">
            <CircleAlert size={27} aria-hidden="true" />
            <div>
              <h2>No pudimos encontrar el envío</h2>
              <p>{trackingQuery.error.message}</p>
              <button type="button" onClick={() => void trackingQuery.refetch()}>
                <RefreshCw size={17} aria-hidden="true" /> Reintentar
              </button>
            </div>
          </section>
        )}

        {!submittedToken && (
          <section className="tracking-feedback">
            <PackageCheck size={29} aria-hidden="true" />
            <div><h2>Tené el código a mano</h2><p>Comienza con <strong>ENV-</strong> y figura en la confirmación del registro.</p></div>
          </section>
        )}

        {trackingQuery.data && (
          <section className="tracking-result" aria-live="polite">
            <header className="tracking-result__header">
              <div>
                <span>Envío</span>
                <h2>{trackingQuery.data.trackingToken}</h2>
              </div>
              <div className="tracking-result__destination">
                <MapPin size={20} aria-hidden="true" />
                <span><small>Destino</small><strong>{trackingQuery.data.destination}</strong></span>
              </div>
              <div className="tracking-result__updated">
                <Clock3 size={18} aria-hidden="true" />
                <span><small>Última actualización</small><strong>{latestUpdate ? formatDate(latestUpdate) : 'No disponible'}</strong></span>
              </div>
            </header>

            <div className="tracking-result__notice">
              <Route size={20} aria-hidden="true" />
              <div><strong>Recorrido operativo</strong><p>La ubicación en tiempo real se verá cuando el repartidor de la ciudad destino comience su recorrido.</p></div>
            </div>

            <div className="tracked-packages">
              {trackingQuery.data.packages.map((shipmentPackage) => (
                <PackageProgress key={shipmentPackage.packageNumber} shipmentPackage={shipmentPackage} />
              ))}
            </div>

            <footer className="tracking-result__footer">
              <span>{trackingQuery.data.packages.length} {trackingQuery.data.packages.length === 1 ? 'paquete asociado' : 'paquetes asociados'}</span>
              <Link to="/envios/nuevo"><PackagePlus size={17} aria-hidden="true" /> Registrar otro envío</Link>
            </footer>
          </section>
        )}
      </div>
    </main>
  )
}
