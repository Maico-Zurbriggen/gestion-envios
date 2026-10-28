import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRightLeft,
  ClipboardCheck,
  Bell,
  CircleCheckBig,
  Copy,
  ExternalLink,
  FileSignature,
  Mail,
  MapPin,
  MessageCircle,
  MessageSquareWarning,
  Package,
  PackagePlus,
  PackageSearch,
  Phone,
  RefreshCw,
  Route,
  Truck,
  UserRound,
  XCircle,
  type LucideIcon,
} from 'lucide-react'
import { useAppSelector } from '../../../app/store'
import { LocationMap, type MapLocation } from '../../../shared/components/LocationMap'
import { Modal } from '../../../shared/components/Modal'
import { PageHeader } from '../../../shared/components/PageHeader'
import { PrintLabelsButton } from '../../../shared/printing/PrintLabelsButton'
import { formatDimensions } from '../../../shared/printing/shipmentLabels'
import { showToast } from '../../../shared/services/toast'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { PackageSearchBar } from '../components/PackageSearchBar'
import { usePackageTrace } from '../hooks/useMonitor'
import { getSignature } from '../services/monitorApi'
import type { PackageTrace, TraceEvent, TraceEventType } from '../types/monitor.types'
import { CLAIM_STATUS_META, CLAIM_TYPE_LABELS, formatDateTime, formatDay, GROUP_META } from '../utils/monitorFormat'

const EVENT_ICONS: Record<TraceEventType, LucideIcon> = {
  registro: PackagePlus,
  estado: ArrowRightLeft,
  recorrido: Route,
  descarga: ClipboardCheck,
  entrega: CircleCheckBig,
  alerta: AlertTriangle,
  reclamo: MessageSquareWarning,
  notificacion: Bell,
}

type TimelineFilter = 'todo' | 'movimientos' | 'entregas' | 'reclamos' | 'avisos'
const TIMELINE_FILTERS: ReadonlyArray<{ id: TimelineFilter; label: string; types: TraceEventType[] }> = [
  { id: 'todo', label: 'Todo', types: [] },
  { id: 'movimientos', label: 'Movimientos', types: ['registro', 'estado', 'recorrido', 'descarga', 'alerta'] },
  { id: 'entregas', label: 'Entregas', types: ['entrega'] },
  { id: 'reclamos', label: 'Reclamos', types: ['reclamo'] },
  { id: 'avisos', label: 'Avisos', types: ['notificacion'] },
]

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    showToast(`Copiado: ${text}`)
  } catch {
    showToast('No pudimos copiar.', 'error')
  }
}

export function PackageTracePage() {
  const { code } = useParams()

  if (!code) {
    return (
      <main className="monitor-page">
        <PageHeader
          icon={PackageSearch}
          title="Trazabilidad"
          description="Escribí o escaneá el número de un paquete para ver todo lo que pasó con él: quién lo movió, dónde estuvo, entregas, firma, avisos y reclamos."
          actions={<BackToPackages />}
        />
        <section className="surface-card trace-start">
          <PackageSearchBar autoFocus />
          <p>
            También se abre tocando un paquete en <Link to="/monitor/paquetes">Paquetes</Link>, donde además podés buscar por código de
            seguimiento, persona o teléfono.
          </p>
        </section>
      </main>
    )
  }

  return <TraceView key={code} code={code} />
}

function BackToPackages() {
  return (
    <Link className="btn btn--ghost" to="/monitor/paquetes">
      <ArrowLeft size={17} aria-hidden="true" />
      Paquetes
    </Link>
  )
}

function TraceView({ code }: { code: string }) {
  const traceQuery = usePackageTrace(code)
  const trace = traceQuery.data
  const [filter, setFilter] = useState<TimelineFilter>('todo')
  const [signatureId, setSignatureId] = useState<string | null>(null)

  if (traceQuery.isPending) {
    return (
      <main className="monitor-page" aria-busy="true">
        <PageHeader icon={PackageSearch} title={code.toUpperCase()} description="Cargando el historial completo…" />
        <div className="trace-layout">
          <span className="skeleton trace-skeleton" />
          <span className="skeleton trace-skeleton" />
        </div>
      </main>
    )
  }

  if (traceQuery.isError || !trace) {
    return (
      <main className="monitor-page">
        <PageHeader icon={PackageSearch} title={code.toUpperCase()} actions={<BackToPackages />} />
        <section className="surface-card trace-start trace-start--compact">
          <PackageSearchBar initialCode={code.toUpperCase()} />
        </section>
        <div className="list-card list-empty" role="alert">
          <PackageSearch size={30} aria-hidden="true" />
          <strong>No pudimos mostrar este paquete</strong>
          <p>{traceQuery.error?.message}</p>
        </div>
      </main>
    )
  }

  const item = trace.package
  const meta = GROUP_META[item.group]
  const types = TIMELINE_FILTERS.find((option) => option.id === filter)?.types ?? []
  const events = (types.length ? trace.timeline.filter((event) => types.includes(event.type)) : trace.timeline).slice().reverse()
  const position = trace.siblings.findIndex((sibling) => sibling.code === item.code)

  return (
    <main className="monitor-page">
      <PageHeader
        icon={meta.icon}
        title={item.code}
        description={
          <>
            <span className={`badge monitor-badge tone-${meta.tone}`}>{item.statusLabel}</span> Último movimiento el{' '}
            {formatDateTime(item.updatedAt)}.
          </>
        }
        actions={
          <>
            <BackToPackages />
            <button className="btn" type="button" onClick={() => void traceQuery.refetch()} disabled={traceQuery.isFetching}>
              <RefreshCw size={17} className={traceQuery.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
              Actualizar
            </button>
            <PrintLabelsButton
              className="btn"
              settingsClassName="btn btn--ghost"
              label="Imprimir etiqueta"
              labels={[
                {
                  packageNumber: item.code,
                  trackingToken: item.trackingToken,
                  recipientName: item.recipientName,
                  destination: item.destination,
                  deliveryType: item.deliveryType,
                  weightKg: item.weightKg,
                  dimensions: formatDimensions(trace.dimensions.length, trace.dimensions.width, trace.dimensions.height),
                  index: position >= 0 ? position + 1 : null,
                  total: trace.siblings.length,
                  date: formatDateTime(new Date().toISOString()),
                  dateCaption: 'Reimpreso',
                },
              ]}
            />
          </>
        }
      />

      <section className="surface-card trace-start trace-start--compact">
        <PackageSearchBar />
      </section>

      <TraceProgress trace={trace} />

      {item.missingAtUnload || item.withoutRoute || item.failedAttempts || item.activeClaims ? (
        <div className="trace-alerts" role="status">
          {item.missingAtUnload ? (
            <p className="trace-alert tone-danger">
              <ClipboardCheck size={18} aria-hidden="true" />
              No apareció al controlar la descarga en la sucursal de destino. Revisá la línea de tiempo.
            </p>
          ) : null}
          {item.withoutRoute ? (
            <p className="trace-alert tone-warning">
              <AlertTriangle size={18} aria-hidden="true" />
              Quedó fuera de los recorridos generados. <Link to="/recorridos">Revisar en recorridos</Link>
            </p>
          ) : null}
          {item.failedAttempts ? (
            <p className="trace-alert tone-danger">
              <XCircle size={18} aria-hidden="true" />
              {item.failedAttempts === 1 ? 'Tuvo una visita fallida.' : `Tuvo ${item.failedAttempts} visitas fallidas.`}
            </p>
          ) : null}
          {item.activeClaims ? (
            <p className="trace-alert tone-warning">
              <MessageSquareWarning size={18} aria-hidden="true" />
              {item.activeClaims === 1 ? 'Hay un reclamo en curso.' : `Hay ${item.activeClaims} reclamos en curso.`}{' '}
              <Link to={`/monitor/reclamos?q=${item.trackingToken}`}>Ver reclamos</Link>
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="trace-layout">
        <section className="surface-card trace-timeline" aria-labelledby="trace-timeline-title">
          <header className="monitor-card__header">
            <div>
              <h2 id="trace-timeline-title">
                <ArrowRightLeft size={18} aria-hidden="true" />
                Línea de tiempo
              </h2>
              <p>Del más reciente al más antiguo. Incluye quién hizo cada movimiento y dónde.</p>
            </div>
          </header>
          <div className="segmented trace-timeline__filters" role="group" aria-label="Filtrar la línea de tiempo">
            {TIMELINE_FILTERS.map((option) => (
              <button key={option.id} type="button" aria-pressed={filter === option.id} onClick={() => setFilter(option.id)}>
                {option.label}
              </button>
            ))}
          </div>
          {events.length ? (
            <ol className="timeline">
              {events.map((event, index) => (
                <TimelineItem key={`${event.date}-${index}`} event={event} onSignature={setSignatureId} />
              ))}
            </ol>
          ) : (
            <p className="trace-empty">No hay movimientos de este tipo.</p>
          )}
        </section>

        <div className="trace-side">
          <section className="surface-card trace-card" aria-labelledby="trace-package-title">
            <h2 id="trace-package-title">
              <Package size={17} aria-hidden="true" />
              Paquete
            </h2>
            <dl className="trace-dl">
              <div><dt>Contenido</dt><dd>{item.description}</dd></div>
              <div><dt>Peso</dt><dd>{item.weightKg} kg</dd></div>
              <div><dt>Medidas</dt><dd>{formatDimensions(trace.dimensions.length, trace.dimensions.width, trace.dimensions.height)}</dd></div>
              <div>
                <dt>Seguimiento</dt>
                <dd className="trace-copy">
                  <span className="monitor-row__token">{item.trackingToken}</span>
                  <button className="icon-action" type="button" aria-label="Copiar código de seguimiento" onClick={() => void copy(item.trackingToken)}>
                    <Copy size={15} aria-hidden="true" />
                  </button>
                  <a className="icon-action" href={`/seguimiento?token=${item.trackingToken}`} target="_blank" rel="noreferrer" aria-label="Abrir el seguimiento público">
                    <ExternalLink size={15} aria-hidden="true" />
                  </a>
                </dd>
              </div>
              <div><dt>Registrado</dt><dd>{formatDateTime(item.createdAt)}</dd></div>
              {item.currentBranch ? <div><dt>Ubicado en</dt><dd>{item.currentBranch}</dd></div> : null}
              {trace.notes ? <div><dt>Observaciones</dt><dd>{trace.notes}</dd></div> : null}
            </dl>
          </section>

          <section className="surface-card trace-card" aria-labelledby="trace-people-title">
            <h2 id="trace-people-title">
              <UserRound size={17} aria-hidden="true" />
              Remitente y destinatario
            </h2>
            <div className="trace-people">
              <PersonBlock role="Envía" person={trace.sender} />
              <PersonBlock role="Recibe" person={trace.recipient} />
            </div>
          </section>

          <section className="surface-card trace-card" aria-labelledby="trace-destination-title">
            <h2 id="trace-destination-title">
              <MapPin size={17} aria-hidden="true" />
              Destino
            </h2>
            <p className="trace-destination">
              <span className="badge badge--muted">{item.deliveryType === 'domicilio' ? 'Entrega a domicilio' : 'Retiro en sucursal'}</span>
              {trace.destinationAddress}
            </p>
            <TraceMap trace={trace} />
          </section>

          {trace.siblings.length > 1 ? (
            <section className="surface-card trace-card" aria-labelledby="trace-siblings-title">
              <h2 id="trace-siblings-title">
                <PackageSearch size={17} aria-hidden="true" />
                Paquetes del mismo envío
              </h2>
              <ul className="trace-siblings">
                {trace.siblings.map((sibling) => (
                  <li key={sibling.code}>
                    {sibling.code === item.code ? (
                      <strong className="monitor-row__code">{sibling.code}</strong>
                    ) : (
                      <Link className="monitor-row__code" to={`/monitor/trazabilidad/${sibling.code}`}>{sibling.code}</Link>
                    )}
                    <span className={`badge monitor-badge tone-${GROUP_META[sibling.group].tone}`}>{sibling.statusLabel}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </div>

      <div className="trace-grid">
        <section className="surface-card trace-card" aria-labelledby="trace-routes-title">
          <h2 id="trace-routes-title">
            <Truck size={17} aria-hidden="true" />
            Recorridos
          </h2>
          {trace.routes.length ? (
            <ul className="trace-list">
              {trace.routes.map((route) => (
                <li key={route.id}>
                  <strong>{formatDay(route.date)} · {route.distanceType === 'CORTA' ? 'Corta distancia' : 'Larga distancia'}</strong>
                  <span>{route.driverName} · sale de {route.originBranch} · parada {route.stop}</span>
                  <span className="trace-list__badges">
                    <span className="badge badge--muted">Recorrido {route.status.replace('_', ' ').toLowerCase()}</span>
                    <span className={`badge ${route.stopStatus === 'ENTREGADO' ? 'badge--success' : route.stopStatus === 'FALLIDO' ? 'badge--danger' : 'badge--muted'}`}>
                      Parada {route.stopStatus.toLowerCase()}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="trace-empty">Todavía no se asignó a ningún recorrido.</p>
          )}
        </section>

        <section className="surface-card trace-card" aria-labelledby="trace-deliveries-title">
          <h2 id="trace-deliveries-title">
            <FileSignature size={17} aria-hidden="true" />
            Entregas y visitas
          </h2>
          {trace.deliveries.length ? (
            <ul className="trace-list">
              {trace.deliveries.map((delivery) => (
                <li key={delivery.id}>
                  <strong>
                    {delivery.successful ? (delivery.kind === 'RETIRO_SUCURSAL' ? 'Retirado en sucursal' : 'Entregado') : 'Visita fallida'} ·{' '}
                    {formatDateTime(delivery.date)}
                  </strong>
                  {delivery.successful ? (
                    <span>
                      Recibió {delivery.receiverName ?? '—'}
                      {delivery.receiverDocument ? ` (DNI ${delivery.receiverDocument})` : ''}
                      {delivery.authorized ? ' · persona autorizada' : ''}
                    </span>
                  ) : (
                    <span>{delivery.failureReason ?? 'Sin motivo informado.'}</span>
                  )}
                  <span>Registró {delivery.registeredBy ?? '—'}{delivery.branch ? ` en ${delivery.branch}` : ''}</span>
                  {delivery.hasSignature ? (
                    <button className="btn btn--ghost trace-signature-button" type="button" onClick={() => setSignatureId(delivery.id)}>
                      <FileSignature size={15} aria-hidden="true" />
                      Ver firma
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="trace-empty">Sin intentos de entrega ni retiros.</p>
          )}
        </section>

        <section className="surface-card trace-card" aria-labelledby="trace-claims-title">
          <h2 id="trace-claims-title">
            <MessageSquareWarning size={17} aria-hidden="true" />
            Reclamos
          </h2>
          {trace.claims.length ? (
            <ul className="trace-list">
              {trace.claims.map((claim) => (
                <li key={claim.id}>
                  <strong>
                    {CLAIM_TYPE_LABELS[claim.type] ?? claim.type} · {formatDateTime(claim.createdAt)}
                  </strong>
                  <span>{claim.description}</span>
                  {claim.resolution ? <span>Respuesta: {claim.resolution}</span> : null}
                  <span className="trace-list__badges">
                    <span className={`badge ${CLAIM_STATUS_META[claim.status]?.badge ?? 'badge--muted'}`}>
                      {CLAIM_STATUS_META[claim.status]?.label ?? claim.status}
                    </span>
                    <Link className="monitor-link" to={`/monitor/reclamos?reclamo=${claim.id}`}>Gestionar</Link>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="trace-empty">No hay reclamos para este paquete.</p>
          )}
        </section>

        <section className="surface-card trace-card" aria-labelledby="trace-notifications-title">
          <h2 id="trace-notifications-title">
            <Bell size={17} aria-hidden="true" />
            Avisos al cliente
          </h2>
          {trace.notifications.length ? (
            <ul className="trace-list">
              {trace.notifications.map((notification, index) => (
                <li key={`${notification.channel}-${notification.destination}-${index}`}>
                  <strong>
                    {notification.channel === 'EMAIL' ? <Mail size={14} aria-hidden="true" /> : <MessageCircle size={14} aria-hidden="true" />}
                    {notification.reason} al {notification.recipientType === 'REMITENTE' ? 'remitente' : 'destinatario'}
                  </strong>
                  <span>{notification.destination} · {formatDateTime(notification.updatedAt)}</span>
                  <span className="trace-list__badges">
                    <span className={`badge ${notification.status === 'ENVIADO' ? 'badge--success' : notification.status === 'FALLIDO' ? 'badge--danger' : 'badge--muted'}`}>
                      {notification.status === 'ENVIADO' ? 'Enviado' : notification.status === 'FALLIDO' ? 'No se pudo enviar' : 'Pendiente'}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="trace-empty">No se enviaron avisos para este envío.</p>
          )}
        </section>
      </div>

      <SignatureModal eventId={signatureId} onClose={() => setSignatureId(null)} />
    </main>
  )
}

function TraceProgress({ trace }: { trace: PackageTrace }) {
  const item = trace.package
  const home = item.deliveryType === 'domicilio'
  const failed = item.group === 'NO_ENTREGADOS'
  // A domicilio: el reparto es una etapa propia; a sucursal, la espera para retirar.
  const reachedByGroup = { PENDIENTES: 0, EN_DEPOSITO: 1, EN_CAMINO: 2, PARA_RETIRAR: 3, NO_ENTREGADOS: 3, ENTREGADOS: 4, OTROS: 0 }
  const reached = home && item.status === 'EN_REPARTO' ? 3 : reachedByGroup[item.group]
  const steps = [
    'Registrado',
    'En terminal',
    'En tránsito',
    home ? (failed ? 'Visita fallida' : 'En reparto') : 'Para retirar',
    home ? 'Entregado' : 'Retirado',
  ]
  return (
    <ol className="trace-progress" aria-label={`Etapa actual: ${item.statusLabel}`}>
      {steps.map((step, index) => {
        const state = index < reached ? 'is-done' : index === reached ? (failed ? 'is-failed' : 'is-current') : ''
        return (
          <li key={step} className={`trace-progress__step ${state}`} aria-current={index === reached ? 'step' : undefined}>
            <span className="trace-progress__dot" aria-hidden="true">{index + 1}</span>
            <span>{step}</span>
          </li>
        )
      })}
    </ol>
  )
}

function TimelineItem({ event, onSignature }: { event: TraceEvent; onSignature: (id: string) => void }) {
  const Icon = event.type === 'entrega' && event.tone === 'danger' ? XCircle : EVENT_ICONS[event.type]
  return (
    <li className={`timeline__item tone-${event.tone}`}>
      <span className="timeline__icon" aria-hidden="true">
        <Icon size={15} />
      </span>
      <div className="timeline__body">
        <p className="timeline__title">
          <strong>{event.title}</strong>
          <time dateTime={event.date}>{formatDateTime(event.date)}</time>
        </p>
        {event.detail ? <p className="timeline__detail">{event.detail}</p> : null}
        <p className="timeline__meta">
          {event.actor ? <span><UserRound size={12} aria-hidden="true" />{event.actor}</span> : null}
          {event.place ? <span><MapPin size={12} aria-hidden="true" />{event.place}</span> : null}
          {event.latitude !== null && event.longitude !== null ? (
            <a href={`https://www.openstreetmap.org/?mlat=${event.latitude}&mlon=${event.longitude}#map=17/${event.latitude}/${event.longitude}`} target="_blank" rel="noreferrer">
              Ver ubicación
            </a>
          ) : null}
          {event.hasSignature && event.deliveryEventId ? (
            <button type="button" className="timeline__link" onClick={() => onSignature(event.deliveryEventId!)}>
              Ver firma
            </button>
          ) : null}
        </p>
      </div>
    </li>
  )
}

function PersonBlock({ role, person }: { role: string; person: PackageTrace['sender'] }) {
  return (
    <div className="trace-person">
      <p className="eyebrow">{role}</p>
      <strong>{person.name}</strong>
      {person.document ? <span>DNI {person.document}</span> : null}
      {person.phone ? (
        <a href={`tel:${person.phone.replace(/[^\d+]/g, '')}`}>
          <Phone size={13} aria-hidden="true" />
          {person.phone}
        </a>
      ) : null}
      {person.email ? (
        <a href={`mailto:${person.email}`}>
          <Mail size={13} aria-hidden="true" />
          {person.email}
        </a>
      ) : null}
    </div>
  )
}

function TraceMap({ trace }: { trace: PackageTrace }) {
  const locations: MapLocation[] = []
  if (trace.destinationLocation) locations.push({ ...trace.destinationLocation, label: 'Destino' })
  for (const delivery of trace.deliveries) {
    if (delivery.location) {
      locations.push({ ...delivery.location, label: `${delivery.successful ? 'Entrega' : 'Visita fallida'} ${formatDateTime(delivery.date)}` })
    }
  }
  if (!locations.length) return <p className="trace-empty">El destino no tiene ubicación en el mapa.</p>
  return <LocationMap locations={locations} name={`Mapa del paquete ${trace.package.code}`} />
}

function SignatureModal({ eventId, onClose }: { eventId: string | null; onClose: () => void }) {
  const token = useAppSelector(selectAuthToken)
  const signature = useQuery({
    queryKey: ['admin', 'monitor', 'signature', eventId],
    queryFn: () => getSignature(eventId ?? '', token ?? ''),
    enabled: Boolean(eventId && token),
    staleTime: Infinity,
    retry: false,
  })
  const url = useMemo(() => (signature.data ? URL.createObjectURL(signature.data) : null), [signature.data])
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url)
  }, [url])

  return (
    <Modal open={Boolean(eventId)} onClose={onClose} icon={FileSignature} eyebrow="Constancia de entrega" title="Firma de quien recibió" size="narrow">
      {signature.isPending ? <span className="skeleton trace-signature-skeleton" /> : null}
      {signature.isError ? (
        <p className="form-error" role="alert">
          <AlertTriangle size={18} aria-hidden="true" />
          {signature.error.message}
        </p>
      ) : null}
      {url ? <img className="trace-signature" src={url} alt="Firma registrada al entregar el paquete" /> : null}
    </Modal>
  )
}
