import { useRef, useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronUp, CircleAlert, LoaderCircle, MessageSquareWarning, RefreshCw } from 'lucide-react'
import { useCreateClaim, useShipmentClaims } from '../hooks/useShipmentClaims'
import type { ClaimFormValues, ClaimStatus, ClaimType } from '../types/claim.types'
import { ClaimForm } from './ClaimForm'
import './ShipmentClaims.css'

const typeLabels: Record<ClaimType, string> = { DEMORA: 'Demora', DANIO: 'Daño', EXTRAVIO: 'Extravío', OTRO: 'Otro inconveniente' }
const statusLabels: Record<ClaimStatus, string> = { ABIERTO: 'Abierto', EN_REVISION: 'En revisión', RESUELTO: 'Resuelto', RECHAZADO: 'Rechazado' }
const dateFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' })

export function ShipmentClaims({ token }: { token: string }) {
  const [expanded, setExpanded] = useState(false)
  const [registered, setRegistered] = useState(false)
  const query = useShipmentClaims(token, expanded)
  const mutation = useCreateClaim(token)
  const successRef = useRef<HTMLDivElement>(null)

  async function handleSubmit(values: ClaimFormValues) {
    setRegistered(false)
    await mutation.mutateAsync(values)
    setRegistered(true)
    requestAnimationFrame(() => successRef.current?.focus())
  }

  return (
    <section className="shipment-claims" aria-labelledby="shipment-claims-title">
      <header className="shipment-claims__header">
        <MessageSquareWarning size={23} aria-hidden="true" />
        <div>
          <h2 id="shipment-claims-title">¿Tenés un inconveniente con este envío?</h2>
          <p>Iniciá un reclamo o consultá la respuesta a uno anterior.</p>
        </div>
        <button className="claim-button" type="button" aria-expanded={expanded} aria-controls="shipment-claims-content" disabled={mutation.isPending} onClick={() => setExpanded(!expanded)}>
          {expanded ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
          {expanded ? 'Ocultar reclamos' : 'Iniciar reclamo'}
        </button>
      </header>
      <div id="shipment-claims-content" hidden={!expanded}>
        {expanded && <div className="shipment-claims__body">
          <p className="shipment-claims__context">Reclamos del envío <strong>{token}</strong></p>
          {registered && <div className="shipment-claims__success" role="status" tabIndex={-1} ref={successRef}>
            <CheckCircle2 size={23} aria-hidden="true" />
            <div><strong>Reclamo registrado</strong><p>Podés consultar su estado y la respuesta desde este mismo código de seguimiento.</p></div>
          </div>}
          {query.isPending && <p className="shipment-claims__loading" role="status"><LoaderCircle size={20} className="loading-icon" aria-hidden="true" /> Cargando los datos del reclamo…</p>}
          {query.isError && <div className="form-error" role="alert"><CircleAlert size={20} aria-hidden="true" /><div><p>{query.error.message}</p><button className="claim-button" type="button" disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={16} aria-hidden="true" /> Reintentar</button></div></div>}
          {query.data && <>
            {query.data.canCreate ? <ClaimForm context={query.data} pending={mutation.isPending} onSubmit={handleSubmit} /> : <div className="shipment-claims__unavailable" role="status"><CircleAlert size={20} aria-hidden="true" /><p>{query.data.unavailableReason || 'No es posible iniciar otro reclamo para este envío en este momento.'}</p></div>}
            <section className="claim-history" aria-labelledby="claim-history-title">
              <header className="claim-history__header">
                <h3 id="claim-history-title">Reclamos anteriores ({query.data.claims.length})</h3>
                <button className="claim-button" type="button" disabled={query.isFetching || mutation.isPending} onClick={() => void query.refetch()}><RefreshCw size={16} className={query.isFetching ? 'loading-icon' : undefined} aria-hidden="true" /> Actualizar</button>
              </header>
              {query.data.claims.length === 0 ? <p className="claim-history__empty">Este envío todavía no tiene reclamos.</p> : <ul className="claim-history__list">
                {query.data.claims.map((claim) => <li key={claim.id} className="claim-history__item">
                  <div className="claim-history__item-header"><strong>{typeLabels[claim.type] ?? 'Reclamo'}</strong><span className={`claim-status claim-status--${claim.status.toLowerCase()}`}>{statusLabels[claim.status] ?? claim.status}</span></div>
                  <small>{claim.packageNumber || 'Todo el envío'}</small>
                  <p className="claim-history__description">{claim.description}</p>
                  {claim.resolution && <div className="claim-history__resolution"><strong>Respuesta</strong><p>{claim.resolution}</p></div>}
                  <footer>Creado <time dateTime={claim.createdAt}>{dateFormatter.format(new Date(claim.createdAt))}</time>{claim.updatedAt !== claim.createdAt && <> · Actualizado <time dateTime={claim.updatedAt}>{dateFormatter.format(new Date(claim.updatedAt))}</time></>}</footer>
                </li>)}
              </ul>}
            </section>
          </>}
        </div>}
      </div>
    </section>
  )
}
