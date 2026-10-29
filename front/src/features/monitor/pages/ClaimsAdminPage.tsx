import { useDeferredValue, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  Eye,
  LoaderCircle,
  Mail,
  MessageSquareWarning,
  PackageSearch,
  Phone,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import { FilterTabs, PageHeader, StatCard } from '../../../shared/components/PageHeader'
import { showToast } from '../../../shared/services/toast'
import { useAdminClaims, useUpdateClaim } from '../hooks/useMonitor'
import { CLAIM_TRANSITIONS, type AdminClaim, type ClaimStatus } from '../services/claimsAdminApi'
import { CLAIM_STATUS_META, CLAIM_TYPE_LABELS, formatDateTime, formatRelative } from '../utils/monitorFormat'

type StatusTab = 'EN_CURSO' | 'TODOS' | ClaimStatus

const ACTION_LABELS: Record<ClaimStatus, string> = {
  ABIERTO: 'Reabrir',
  EN_REVISION: 'Pasar a revisión',
  RESUELTO: 'Marcar como resuelto',
  RECHAZADO: 'Rechazar',
}

function normalize(text: string) {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

export function ClaimsAdminPage() {
  const [params, setParams] = useSearchParams()
  const [tab, setTab] = useState<StatusTab>('EN_CURSO')
  const [type, setType] = useState('')
  const [search, setSearch] = useState(() => params.get('q') ?? '')
  const deferredSearch = useDeferredValue(search)
  const claimsQuery = useAdminClaims()
  const claims = claimsQuery.data ?? []
  const selectedId = params.get('reclamo')
  const selected = claims.find((claim) => claim.id === selectedId) ?? null

  const counts = {
    TODOS: claims.length,
    EN_CURSO: claims.filter((claim) => claim.status === 'ABIERTO' || claim.status === 'EN_REVISION').length,
    ABIERTO: claims.filter((claim) => claim.status === 'ABIERTO').length,
    EN_REVISION: claims.filter((claim) => claim.status === 'EN_REVISION').length,
    RESUELTO: claims.filter((claim) => claim.status === 'RESUELTO').length,
    RECHAZADO: claims.filter((claim) => claim.status === 'RECHAZADO').length,
  }

  const terms = normalize(deferredSearch).split(/\s+/).filter(Boolean)
  const visible = claims.filter((claim) => {
    if (tab === 'EN_CURSO' && !(claim.status === 'ABIERTO' || claim.status === 'EN_REVISION')) return false
    if (tab !== 'EN_CURSO' && tab !== 'TODOS' && claim.status !== tab) return false
    if (type && claim.type !== type) return false
    const haystack = normalize(
      [claim.trackingToken, claim.packageCode, claim.contactName, claim.contactEmail, claim.contactPhone, claim.senderName, claim.recipientName, claim.description].join(' '),
    )
    return terms.every((term) => haystack.includes(term))
  })

  function openClaim(id: string | null) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (id) next.set('reclamo', id)
        else next.delete('reclamo')
        return next
      },
      { replace: true },
    )
  }

  return (
    <main className="monitor-page">
      <PageHeader
        icon={MessageSquareWarning}
        title="Reclamos"
        description="Los reclamos que inician los clientes desde el seguimiento. Revisalos, respondé y cerralos: la respuesta se muestra en el seguimiento público."
        actions={
          <button className="btn" type="button" onClick={() => void claimsQuery.refetch()} disabled={claimsQuery.isFetching}>
            <RefreshCw size={17} className={claimsQuery.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
            Actualizar
          </button>
        }
      />

      <section className="stat-grid" aria-label="Resumen de reclamos">
        <StatCard label="Abiertos" value={claimsQuery.data ? counts.ABIERTO : '—'} icon={CircleAlert} hint="Sin revisar todavía" />
        <StatCard label="En revisión" value={claimsQuery.data ? counts.EN_REVISION : '—'} icon={Clock3} tone="info" hint="Alguien los está atendiendo" />
        <StatCard label="Resueltos" value={claimsQuery.data ? counts.RESUELTO : '—'} icon={CheckCircle2} tone="success" hint="Con respuesta al cliente" />
        <StatCard label="Rechazados" value={claimsQuery.data ? counts.RECHAZADO : '—'} icon={XCircle} tone="muted" hint="Cerrados sin lugar" />
      </section>

      <FilterTabs<StatusTab>
        label="Filtrar por estado"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'EN_CURSO', label: 'En curso', count: counts.EN_CURSO },
          { id: 'ABIERTO', label: 'Abiertos', count: counts.ABIERTO },
          { id: 'EN_REVISION', label: 'En revisión', count: counts.EN_REVISION },
          { id: 'RESUELTO', label: 'Resueltos', count: counts.RESUELTO },
          { id: 'RECHAZADO', label: 'Rechazados', count: counts.RECHAZADO },
          { id: 'TODOS', label: 'Todos', count: counts.TODOS },
        ]}
      />

      <section className="list-card" aria-labelledby="claims-list-title">
        <div className="list-toolbar">
          <h2 className="list-toolbar__title" id="claims-list-title">
            Bandeja
            <small>{claimsQuery.data ? `${visible.length} ${visible.length === 1 ? 'reclamo' : 'reclamos'}` : ''}</small>
          </h2>
          <div className="list-toolbar__controls">
            <label className="visually-hidden" htmlFor="claims-type">Tipo de reclamo</label>
            <select className="list-select" id="claims-type" value={type} onChange={(event) => setType(event.target.value)}>
              <option value="">Todos los tipos</option>
              {Object.entries(CLAIM_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <div className="list-search">
              <Search size={16} aria-hidden="true" />
              <label className="visually-hidden" htmlFor="claims-search">Buscar reclamos</label>
              <input
                id="claims-search"
                type="search"
                placeholder="Código, paquete, persona o texto"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>
        </div>

        {claimsQuery.isPending ? (
          <ul className="list-rows" aria-busy="true" aria-label="Cargando reclamos">
            {[0, 1, 2].map((item) => (
              <li className="list-row" key={item}>
                <span className="skeleton monitor-skeleton__icon" />
                <span className="monitor-skeleton__lines">
                  <span className="skeleton" />
                  <span className="skeleton" />
                </span>
              </li>
            ))}
          </ul>
        ) : claimsQuery.isError ? (
          <div className="list-empty" role="alert">
            <MessageSquareWarning size={30} aria-hidden="true" />
            <strong>No pudimos cargar los reclamos</strong>
            <p>{claimsQuery.error.message}</p>
          </div>
        ) : visible.length === 0 ? (
          <div className="list-empty">
            <CheckCircle2 size={30} aria-hidden="true" />
            <strong>{claims.length ? 'Ningún reclamo coincide con el filtro' : 'No hay reclamos'}</strong>
            <p>{tab === 'EN_CURSO' && !search ? 'No queda ningún reclamo por atender.' : 'Probá con otro estado, tipo o búsqueda.'}</p>
          </div>
        ) : (
          <ul className="list-rows">
            {visible.map((claim) => {
              const meta = CLAIM_STATUS_META[claim.status]
              return (
                <li className={`list-row monitor-row tone-${meta.tone}`} key={claim.id}>
                  <span className="monitor-row__icon" aria-hidden="true">
                    <MessageSquareWarning size={18} />
                  </span>
                  <div className="list-row__main">
                    <p className="list-row__title">
                      {CLAIM_TYPE_LABELS[claim.type] ?? claim.type}
                      <span className={`badge ${meta.badge}`}>{meta.label}</span>
                      <span className="monitor-row__token">{claim.packageCode ?? claim.trackingToken}</span>
                    </p>
                    <p className="list-row__meta claims-row__text">{claim.description}</p>
                    <p className="list-row__meta">
                      <span>{claim.contactName}</span>
                      <span>Envío de {claim.senderName} a {claim.recipientName}</span>
                      <span title={formatDateTime(claim.createdAt)}>Iniciado {formatRelative(claim.createdAt)}</span>
                    </p>
                  </div>
                  <div className="list-row__aside">
                    <button className="btn" type="button" onClick={() => openClaim(claim.id)}>
                      <Eye size={16} aria-hidden="true" />
                      {claim.status === 'ABIERTO' || claim.status === 'EN_REVISION' ? 'Atender' : 'Ver'}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <ClaimModal key={selected?.id ?? 'none'} claim={selected} onClose={() => openClaim(null)} />
    </main>
  )
}

function ClaimModal({ claim, onClose }: { claim: AdminClaim | null; onClose: () => void }) {
  const [resolution, setResolution] = useState(claim?.resolution ?? '')
  const update = useUpdateClaim()
  const meta = claim ? CLAIM_STATUS_META[claim.status] : null
  const transitions = claim ? CLAIM_TRANSITIONS[claim.status] : []
  const closing = (status: ClaimStatus) => status === 'RESUELTO' || status === 'RECHAZADO'

  function apply(status: ClaimStatus) {
    if (!claim) return
    update.mutate(
      { id: claim.id, status, resolution },
      {
        onSuccess: (updated) => {
          showToast(`Reclamo ${CLAIM_STATUS_META[updated.status].label.toLowerCase()}.`)
          if (closing(status)) onClose()
        },
      },
    )
  }

  return (
    <Modal
      open={Boolean(claim)}
      onClose={onClose}
      size="wide"
      icon={MessageSquareWarning}
      eyebrow={claim ? `Reclamo por ${CLAIM_TYPE_LABELS[claim.type]?.toLowerCase() ?? claim.type}` : undefined}
      title={claim ? (claim.packageCode ?? claim.trackingToken) : ''}
      description={claim ? `Iniciado el ${formatDateTime(claim.createdAt)} · ${meta?.label}` : undefined}
    >
      {claim ? (
        <div className="claim-detail">
          <section>
            <h3>Qué pasó</h3>
            <p className="claim-detail__text">{claim.description}</p>
          </section>

          <div className="claim-detail__grid">
            <section>
              <h3>Contacto</h3>
              <p><strong>{claim.contactName}</strong></p>
              {claim.contactPhone ? (
                <p><a href={`tel:${claim.contactPhone.replace(/[^\d+]/g, '')}`}><Phone size={14} aria-hidden="true" /> {claim.contactPhone}</a></p>
              ) : null}
              {claim.contactEmail ? (
                <p><a href={`mailto:${claim.contactEmail}`}><Mail size={14} aria-hidden="true" /> {claim.contactEmail}</a></p>
              ) : null}
            </section>
            <section>
              <h3>Envío</h3>
              <p>De {claim.senderName} a {claim.recipientName}</p>
              <p className="monitor-row__token">{claim.trackingToken}</p>
              {claim.packageCode ? (
                <Link className="monitor-link" to={`/monitor/trazabilidad/${claim.packageCode}`}>
                  <PackageSearch size={15} aria-hidden="true" />
                  Ver la trazabilidad del paquete
                </Link>
              ) : (
                <Link className="monitor-link" to={`/monitor/paquetes?q=${claim.trackingToken}`}>
                  <PackageSearch size={15} aria-hidden="true" />
                  Ver los paquetes del envío
                </Link>
              )}
            </section>
          </div>

          {transitions.length ? (
            <section className="claim-detail__answer">
              <div className="form-field">
                <label htmlFor="claim-resolution">Respuesta para el cliente</label>
                <textarea
                  id="claim-resolution"
                  className="form-control"
                  rows={4}
                  maxLength={2000}
                  placeholder="Contale qué se hizo o qué va a pasar. Es obligatoria para resolver o rechazar."
                  value={resolution}
                  onChange={(event) => setResolution(event.target.value)}
                />
                <span className="email-field-hint">Se muestra en el seguimiento público del envío al cerrar el reclamo.</span>
              </div>
              {update.error ? (
                <p className="form-error" role="alert">
                  <CircleAlert size={18} aria-hidden="true" />
                  {update.error.message}
                </p>
              ) : null}
              <div className="claim-detail__actions">
                {transitions.map((status) => (
                  <button
                    key={status}
                    className={`btn ${status === 'RESUELTO' ? 'btn--primary' : status === 'RECHAZADO' ? 'btn--ghost' : ''}`}
                    type="button"
                    disabled={update.isPending || (closing(status) && !resolution.trim())}
                    onClick={() => apply(status)}
                  >
                    {update.isPending && update.variables?.status === status ? (
                      <LoaderCircle className="loading-icon" size={16} aria-hidden="true" />
                    ) : null}
                    {ACTION_LABELS[status]}
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <section className="claim-detail__closed">
              <h3>Respuesta</h3>
              <p>{claim.resolution ?? 'Sin respuesta registrada.'}</p>
              <p className="email-field-hint">
                {claim.resolvedBy ? `Cerrado por ${claim.resolvedBy}` : 'Cerrado'} el {formatDateTime(claim.updatedAt)}.
              </p>
            </section>
          )}
        </div>
      ) : null}
    </Modal>
  )
}
