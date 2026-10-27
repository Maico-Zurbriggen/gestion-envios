import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CheckCircle2, Phone, RefreshCw, X } from 'lucide-react'
import { OperationalApiError } from '../../../shared/services/operationalApi'
import { useDeliveryOperation, useRecipientContact } from '../hooks/useDelivery'
import type { DeliveryOperation } from '../types/delivery.types'
import { receiverIsOldEnough } from '../deliveryValidation'
import { SignaturePad } from './SignaturePad'

export function DeliveryAction({ routeId, code, onClose }: { routeId: string; code: string; onClose: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [])
  const contact = useRecipientContact(routeId, code)
  const mutation = useDeliveryOperation(routeId, code)
  const [mode, setMode] = useState<'delivery' | 'failed'>('delivery')
  const [name, setName] = useState('')
  const [document, setDocument] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [authorized, setAuthorized] = useState(false)
  const [signature, setSignature] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [operation, setOperation] = useState<DeliveryOperation | null>(null)
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    if (operation) { mutation.mutate(operation); return }
    if (mode === 'delivery' && (!receiverIsOldEnough(birthDate) || !signature || name.trim().length < 2 || !document.trim())) { setError('Completá los datos, la firma y una fecha de nacimiento válida. El receptor debe ser mayor de 16 años (el día del cumpleaños 16 no alcanza).'); return }
    if (mode === 'failed' && reason.trim().length < 3) { setError('Ingresá un motivo de al menos 3 caracteres.'); return }
    const input: DeliveryOperation = mode === 'failed' ? { operationId: crypto.randomUUID(), action: 'failed', reason: reason.trim() } : { operationId: crypto.randomUUID(), action: 'delivery', receiver: { name: name.trim(), document: document.trim(), birthDate, authorized, signature } }
    setOperation(input); mutation.mutate(input)
  }
  const correctable = mutation.isError && mutation.error instanceof OperationalApiError && [400, 422].includes(mutation.error.status ?? 0)
  const conflict = mutation.isError && mutation.error instanceof OperationalApiError && mutation.error.status === 409
  const locked = mutation.isPending || Boolean(operation)
  const phone = contact.data?.phone?.replace(/[^\d+]/g, '')
  return <section className="ops-panel ops-stack" aria-labelledby="delivery-action-title">
    <h3 ref={heading} tabIndex={-1} id="delivery-action-title">Registrar resultado · {code}</h3>
    {contact.isPending && <p role="status">Consultando contacto…</p>}
    {contact.isError && <div role="alert"><p>{contact.error.message}</p><button className="ops-button" type="button" onClick={() => void contact.refetch()} disabled={contact.isFetching}><RefreshCw size={18} aria-hidden="true" /> Reintentar contacto</button></div>}
    {contact.data && <p>Destinatario: {contact.data.name}. {phone ? <a className="ops-button" href={`tel:${phone}`}><Phone size={18} aria-hidden="true" /> Llamar al destinatario</a> : 'No hay teléfono disponible.'}</p>}
    {mutation.data ? <div className="ops-success" role="status"><p><CheckCircle2 size={20} aria-hidden="true" /> {operation?.action === 'failed' ? 'Visita fallida registrada. Se solicitó el aviso por email; su entrega depende del servicio de correo.' : 'Entrega y firma registradas.'}</p><p>Constancia: {mutation.data.eventId}</p><p>{new Date(mutation.data.occurredAt).toLocaleString('es-AR')}</p><button className="ops-button" type="button" onClick={onClose}><CheckCircle2 size={18} aria-hidden="true" /> Continuar recorrido</button></div> : <form className="ops-stack" onSubmit={submit}>
      <fieldset className="ops-stack" disabled={locked}>
        <label className="form-field" htmlFor="delivery-mode">Resultado de la visita<select className="form-control" id="delivery-mode" value={mode} onChange={(e) => setMode(e.target.value as 'delivery' | 'failed')}><option value="delivery">Entrega con firma</option><option value="failed">Visita fallida</option></select></label>
        {mode === 'delivery' ? <>
          <label className="form-field" htmlFor="receiver-name">Nombre completo de quien recibe<input className="form-control" id="receiver-name" required minLength={2} maxLength={150} value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label className="form-field" htmlFor="receiver-document">Documento del receptor<input className="form-control" id="receiver-document" required maxLength={20} value={document} onChange={(e) => setDocument(e.target.value)} /></label>
          <label className="form-field" htmlFor="receiver-birthdate">Fecha de nacimiento del receptor<input className="form-control" id="receiver-birthdate" type="date" required max={new Date().toISOString().slice(0, 10)} value={birthDate} onChange={(e) => setBirthDate(e.target.value)} /></label>
          <label className="ops-check" htmlFor="receiver-authorized"><input id="receiver-authorized" type="checkbox" checked={authorized} onChange={(e) => setAuthorized(e.target.checked)} /> Recibe una persona autorizada en lugar del destinatario</label>
          <SignaturePad onChange={setSignature} disabled={locked} />
        </> : <label className="form-field" htmlFor="failure-reason">Motivo de la visita fallida<textarea id="failure-reason" className="form-control" required minLength={3} maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} /></label>}
      </fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
      {mutation.isError && <div className="form-error ops-stack" role="alert"><p>{mutation.error.message}</p><p>{conflict ? 'La operación entra en conflicto con un registro existente. Volvé al recorrido y revisá el estado antes de continuar.' : 'El reintento conserva los mismos datos y código de operación. Mantené esta pantalla abierta para recuperar la constancia.'}</p></div>}
      <div className="ops-actions"><button className="ops-button" disabled={mutation.isPending}><CheckCircle2 size={18} aria-hidden="true" />{mutation.isPending ? 'Registrando…' : operation ? 'Reintentar la misma operación' : mode === 'delivery' ? 'Confirmar entrega' : 'Confirmar visita fallida'}</button>
        {correctable && <button className="ops-button" type="button" onClick={() => { setOperation(null); mutation.reset() }}><RefreshCw size={18} aria-hidden="true" /> Corregir datos</button>}
        {conflict && <button className="ops-button" type="button" onClick={onClose}><RefreshCw size={18} aria-hidden="true" /> Revisar estado del recorrido</button>}
        {!operation && <button className="ops-button" type="button" onClick={onClose}><X size={18} aria-hidden="true" /> Cancelar</button>}
      </div>
    </form>}
  </section>
}
