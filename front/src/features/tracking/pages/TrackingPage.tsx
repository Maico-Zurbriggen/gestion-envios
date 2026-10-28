import { useState, type FormEvent } from 'react'
import {
  Box,
  Building2,
  CalendarClock,
  Check,
  CircleAlert,
  CircleHelp,
  Clock3,
  History,
  House,
  LoaderCircle,
  MapPin,
  PackageCheck,
  PackagePlus,
  RefreshCw,
  Route,
  Search,
  Truck,
  Undo2,
  Warehouse,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useInsidePanel } from '../../../layouts/MainLayout/panelContext'
import { ShipmentClaims } from '../../claims/components/ShipmentClaims'
import { useShipmentTracking } from '../hooks/useShipmentTracking'
import type { TrackedPackage } from '../types/tracking.types'
import { getStatusLabel, getStatusStep, type TrackingDeliveryType } from '../trackingStatus'
import { PickupBranchInfo } from '../components/PickupBranchInfo'
import { LocationMap, type MapLocation } from '../../../shared/components/LocationMap'
import { Modal } from '../../../shared/components/Modal'
import { formatLongDay, parseApiDate } from '../../../shared/utils/dates'
import './TrackingPage.css'
import { PublicHeader } from '../../../shared/components/PublicHeader'

const HOME_TRACKING_STEPS = [
  { label: 'Registrado', description: 'Código de seguimiento generado', icon: Check },
  { label: 'En sucursal', description: 'Recibido para despacho', icon: Warehouse },
  { label: 'En viaje', description: 'Traslado hacia el destino', icon: Truck },
  { label: 'Entregado', description: 'Recepción confirmada', icon: House },
] as const

const PICKUP_TRACKING_STEPS = [
  { label: 'Registrado', description: 'Código de seguimiento generado', icon: Check },
  { label: 'Recibido', description: 'Ingresó en la terminal', icon: Warehouse },
  { label: 'En viaje', description: 'Traslado a la sucursal', icon: Truck },
  { label: 'Para retirar', description: 'Disponible en sucursal', icon: Building2 },
  { label: 'Retirado', description: 'Entrega verificada', icon: PackageCheck },
] as const

function normalizeToken(value: string) {
  return value.toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 30)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parseApiDate(value))
}

const CLOSED_STATUSES = new Set(['ENTREGADO', 'ENTREGADO_EN_SUCURSAL', 'RETIRADO', 'DEVUELTO'])

/** Lo que el destinatario tiene que saber o hacer ahora con este paquete. */
function PackageNotices({ shipmentPackage }: { shipmentPackage: TrackedPackage }) {
  const { status, pickup, failedVisits, maxVisits, isReturn } = shipmentPackage
  const closed = CLOSED_STATUSES.has(status)
  return (
    <>
      {status === 'VENCIDO' && (
        <p className="tracking-notice tracking-notice--danger" role="status">
          <CircleAlert size={18} aria-hidden="true" />
          <span>El paquete no se llevó a una sucursal dentro de los 10 días del registro y el código venció. Para enviarlo, registrá un envío nuevo.</span>
        </p>
      )}
      {status === 'DEVUELTO' && (
        <p className="tracking-notice" role="status">
          <Undo2 size={18} aria-hidden="true" />
          <span>No se retiró a tiempo y ya se devolvió a quien lo envió.</span>
        </p>
      )}
      {isReturn && !closed && (
        <p className="tracking-notice tracking-notice--warning" role="status">
          <Undo2 size={18} aria-hidden="true" />
          <span>No se retiró dentro del plazo: el paquete vuelve a la sucursal de origen para que lo retire quien lo envió.</span>
        </p>
      )}
      {status === 'ENTREGA_FALLIDA' && <p role="status">La visita no pudo completarse. El paquete aún no fue entregado.</p>}
      {failedVisits > 0 && !closed && !isReturn && (
        <p className="tracking-notice tracking-notice--warning" role="status">
          <House size={18} aria-hidden="true" />
          <span>
            {failedVisits >= maxVisits
              ? `Se hicieron las ${maxVisits} visitas a domicilio sin poder entregarlo. Ahora hay que retirarlo en la sucursal.`
              : `Visita a domicilio sin entrega: ${failedVisits} de ${maxVisits}. Se vuelve a intentar en el próximo reparto.`}
          </span>
        </p>
      )}
      {pickup && !closed && (
        <div className="tracking-pickup-notice" role="status">
          <Building2 size={20} aria-hidden="true" />
          <div>
            <strong>Para retirar en {pickup.branch}</strong>
            <span>{pickup.address}</span>
            {pickup.until && <span>Tenés tiempo hasta el <strong>{formatLongDay(pickup.until)}</strong>.</span>}
            <small>
              {pickup.pickedUpBy === 'remitente'
                ? 'Lo retira quien lo envió, con DNI y el código del envío.'
                : 'Lo retira el destinatario con DNI y el código del envío, o un tercero autorizado.'}
            </small>
          </div>
        </div>
      )}
    </>
  )
}

function PackageProgress({ shipmentPackage, deliveryType }: { shipmentPackage: TrackedPackage; deliveryType: TrackingDeliveryType }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const currentStep = getStatusStep(shipmentPackage.status, deliveryType)
  const steps = deliveryType === 'sucursal' ? PICKUP_TRACKING_STEPS : HOME_TRACKING_STEPS

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
        <span className="tracked-package__status" title={shipmentPackage.status}>{getStatusLabel(shipmentPackage.status)}</span>
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
          {steps.map((step, index) => {
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

        <PackageNotices shipmentPackage={shipmentPackage} />
        {shipmentPackage.history.length > 0 && <>
          <button className="tracked-package__history-button" type="button" aria-haspopup="dialog" onClick={() => setHistoryOpen(true)}>
            <History size={17} aria-hidden="true" /> Ver historial real del paquete <span className="badge badge--muted">{shipmentPackage.history.length}</span>
          </button>
          <Modal open={historyOpen} onClose={() => setHistoryOpen(false)} eyebrow="Seguimiento" title="Historial real del paquete" description={shipmentPackage.packageNumber} icon={History}>
            <ol className="tracking-history">{shipmentPackage.history.map((event, index) => <li key={`${event.occurredAt}-${index}`}><time dateTime={event.occurredAt}>{formatDate(event.occurredAt)}</time><strong>{event.description}</strong><span className="badge badge--muted">{getStatusLabel(event.status)}</span></li>)}</ol>
          </Modal>
        </>}
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
  const insidePanel = useInsidePanel()
  const trackingQuery = useShipmentTracking(submittedToken)
  const locations: MapLocation[] = []
  const tracking = trackingQuery.data
  if (tracking?.latitude != null && tracking.longitude != null) locations.push({ latitude: tracking.latitude, longitude: tracking.longitude, label: 'Destino del envío' })
  const seenPositions = new Set<string>()
  for (const item of tracking?.packages ?? []) {
    const position = item.driverLocation
    if (!position) continue
    const key = `${position.latitude}-${position.longitude}-${position.updatedAt}`
    if (seenPositions.has(key)) continue
    seenPositions.add(key)
    locations.push({ latitude: position.latitude, longitude: position.longitude, label: `Última posición del reparto · ${formatDate(position.updatedAt)}` })
  }

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
    <main className={`tracking-page${insidePanel ? ' is-embedded' : ''}`}>
      {!insidePanel && <PublicHeader />}

      <div className="tracking-page__content">
        <section className="tracking-hero" aria-labelledby="tracking-title">
          <div>
            <span className="eyebrow"><Route size={15} aria-hidden="true" /> Seguimiento público</span>
            <h1 id="tracking-title">¿Dónde está tu paquete?</h1>
            <p>Ingresá el código de seguimiento del envío. No necesitás iniciar sesión.</p>
            <Link className="tracking-help" to="/preguntas-frecuentes"><CircleHelp size={17} aria-hidden="true" /> Preguntas frecuentes</Link>
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
                <span><small>{trackingQuery.data.deliveryType === 'sucursal' ? 'Retiro en sucursal' : 'Entrega a domicilio'}</small><strong>{trackingQuery.data.destination}</strong></span>
              </div>
              <div className="tracking-result__updated">
                <Clock3 size={18} aria-hidden="true" />
                <span><small>Última actualización</small><strong>{latestUpdate ? formatDate(latestUpdate) : 'No disponible'}</strong></span>
              </div>
            </header>

            <div className="tracking-result__notice">
              <Route size={20} aria-hidden="true" />
              <div><strong>Ubicación del envío</strong><p>El destino es fijo. La posición del reparto se muestra únicamente mientras el paquete está pendiente en un recorrido activo; la fecha indica cuándo se recibió la última ubicación. Durante el traslado, la consulta se actualiza cada 15 segundos.</p></div>
            </div>
            {trackingQuery.data.deliveryType === 'sucursal' && (
              <PickupBranchInfo
                token={trackingQuery.data.trackingToken}
                statusKey={trackingQuery.data.packages.map((item) => item.status).join('|')}
              />
            )}
            {locations.length ? <LocationMap locations={locations} name="Destino y última ubicación disponible del reparto" /> : <p role="status">Ubicación no disponible para este envío.</p>}

            <div className="tracked-packages">
              {trackingQuery.data.packages.map((shipmentPackage) => (
                <PackageProgress key={shipmentPackage.packageNumber} shipmentPackage={shipmentPackage} deliveryType={trackingQuery.data.deliveryType} />
              ))}
            </div>

            <ShipmentClaims key={trackingQuery.data.trackingToken} token={trackingQuery.data.trackingToken} />

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
