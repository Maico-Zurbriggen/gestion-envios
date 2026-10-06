import { useState, type FormEvent } from 'react'
import { BadgeCheck, Building2, CircleAlert, ClipboardCheck, IdCard, LoaderCircle, PackageCheck, RefreshCw, Search, UserRound, UsersRound } from 'lucide-react'
import { usePickupValidation, useRegisterPickup } from '../hooks/usePickup'
import type { PickupType, RegisteredPickup } from '../types/pickup.types'
import './PickupPage.css'

const READY_FOR_PICKUP = new Set(['LISTO_PARA_RETIRO', 'EN_SUCURSAL', 'EN_SUCURSAL_DESTINO'])

export function PickupPage() {
  const [codeInput, setCodeInput] = useState('')
  const [searchedCode, setSearchedCode] = useState('')
  const [type, setType] = useState<PickupType>('TITULAR')
  const [documentType, setDocumentType] = useState('DNI')
  const [documentNumber, setDocumentNumber] = useState('')
  const [authorizedName, setAuthorizedName] = useState('')
  const [recipientOver16, setRecipientOver16] = useState(false)
  const [documentReviewed, setDocumentReviewed] = useState(false)
  const [branchVerified, setBranchVerified] = useState(false)
  const [hasRecipientDocumentCopy, setHasRecipientDocumentCopy] = useState(false)
  const [hasSignedAuthorization, setHasSignedAuthorization] = useState(false)
  const [notes, setNotes] = useState('')
  const [completed, setCompleted] = useState<RegisteredPickup | null>(null)
  const validation = usePickupValidation(searchedCode)
  const registration = useRegisterPickup()
  const packageInfo = validation.isSuccess && !validation.isFetching ? validation.data : null
  const branch = packageInfo?.destinationBranch
  const readyStatus = READY_FOR_PICKUP.has(packageInfo?.status ?? '')
  const branchMatches = Boolean(packageInfo?.currentBranch && branch && packageInfo.currentBranch.id === branch.id)
  const eligible = Boolean(packageInfo?.available && readyStatus && packageInfo.deliveryType === 'sucursal' && branchMatches)
  const canRegister = Boolean(
    eligible &&
    recipientOver16 && documentReviewed && branchVerified && documentNumber.trim() &&
    (type === 'TITULAR' || (authorizedName.trim().length >= 2 && hasRecipientDocumentCopy && hasSignedAuthorization)),
  )

  function searchPackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const code = codeInput.trim().toUpperCase()
    if (!code) return
    setCompleted(null)
    registration.reset()
    setType('TITULAR')
    setDocumentType('DNI')
    setDocumentNumber('')
    setAuthorizedName('')
    setRecipientOver16(false)
    setDocumentReviewed(false)
    setBranchVerified(false)
    setHasRecipientDocumentCopy(false)
    setHasSignedAuthorization(false)
    setNotes('')
    if (code === searchedCode) void validation.refetch()
    else setSearchedCode(code)
  }

  function submitPickup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!packageInfo || !canRegister || registration.isPending) return
    registration.mutate({
      packageId: packageInfo.packageId,
      type,
      documentType: documentType.trim(),
      documentNumber: documentNumber.trim(),
      recipientOver16,
      authorizedName: authorizedName.trim(),
      hasRecipientDocumentCopy,
      hasSignedAuthorization,
      notes,
    }, { onSuccess: setCompleted })
  }

  function nextPackage() {
    setCodeInput('')
    setSearchedCode('')
    setType('TITULAR')
    setDocumentType('DNI')
    setDocumentNumber('')
    setAuthorizedName('')
    setRecipientOver16(false)
    setDocumentReviewed(false)
    setBranchVerified(false)
    setHasRecipientDocumentCopy(false)
    setHasSignedAuthorization(false)
    setNotes('')
    setCompleted(null)
    registration.reset()
  }

  return (
    <main className="pickup-page">
      <header className="pickup-page__intro">
        <span className="eyebrow"><Building2 size={16} aria-hidden="true" /> Operación de sucursal</span>
        <h1>Registrar retiro</h1>
        <p>Buscá el paquete, comprobá la identidad y registrá la entrega presencial.</p>
      </header>

      <section className="pickup-panel" aria-labelledby="pickup-search-title">
        <div className="pickup-panel__heading"><Search size={21} aria-hidden="true" /><div><h2 id="pickup-search-title">Buscar paquete</h2><p>Ingresá el código que figura en la etiqueta.</p></div></div>
        <form className="pickup-search" onSubmit={searchPackage}>
          <div className="form-field"><label htmlFor="pickup-code">Código de paquete</label><input className="form-control" id="pickup-code" value={codeInput} onChange={(event) => setCodeInput(event.target.value.toUpperCase())} placeholder="PAQ-XXXXXXXXXX" autoComplete="off" maxLength={40} required /></div>
          <button className="pickup-button" type="submit" disabled={validation.isFetching || registration.isPending || !codeInput.trim()}>{validation.isFetching ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <Search size={18} aria-hidden="true" />}{validation.isFetching ? 'Buscando…' : 'Buscar'}</button>
        </form>
        {validation.isError && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{validation.error.message}</p>}
      </section>

      {completed && <section className="pickup-panel pickup-success" aria-live="polite"><BadgeCheck size={29} aria-hidden="true" /><div><h2>Retiro registrado</h2><p>El paquete <strong>{completed.packageNumber}</strong> figura como <strong>{completed.status}</strong>.</p><dl><div><dt>Recibió</dt><dd>{completed.recipientName} · {completed.recipientDocument}</dd></div><div><dt>Registró</dt><dd>{completed.operatorName}</dd></div><div><dt>Fecha y hora</dt><dd>{new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(completed.deliveredAt))}</dd></div></dl><button type="button" onClick={nextPackage}><RefreshCw size={17} aria-hidden="true" /> Procesar otro paquete</button></div></section>}

      {packageInfo && !completed && (
        <>
          <section className="pickup-panel" aria-labelledby="pickup-package-title">
            <div className="pickup-panel__heading"><PackageCheck size={21} aria-hidden="true" /><div><h2 id="pickup-package-title">Paquete {packageInfo.packageNumber}</h2><p>Confirmá que los datos coincidan con la etiqueta y el envío.</p></div></div>
            <dl className="pickup-summary">
              <div><dt>Estado</dt><dd>{packageInfo.status}</dd></div>
              <div><dt>Contenido</dt><dd>{packageInfo.description}</dd></div>
              <div><dt>Destinatario</dt><dd>{packageInfo.recipient.name}</dd></div>
              <div><dt>Sucursal de retiro</dt><dd>{packageInfo.destinationBranch ? `${packageInfo.destinationBranch.nombre} · ${packageInfo.destinationBranch.direccion}, ${packageInfo.destinationBranch.ciudad}` : 'Sin sucursal asignada'}</dd></div>
              {packageInfo.currentBranch && <div><dt>Sucursal actual</dt><dd>{packageInfo.currentBranch.nombre} · {packageInfo.currentBranch.direccion}, {packageInfo.currentBranch.ciudad}</dd></div>}
            </dl>
            {!eligible && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{packageInfo.deliveryType !== 'sucursal' ? 'Este envío tiene entrega a domicilio y no puede retirarse en sucursal.' : !readyStatus ? 'El paquete aún no fue recibido y habilitado para retiro en sucursal.' : !branchMatches ? 'El paquete debe estar en la sucursal asignada para retiro.' : packageInfo.unavailableReason ?? 'El paquete aún no está disponible para retiro en sucursal.'}</p>}
          </section>

          {eligible && (
            <form className="pickup-panel pickup-form" onSubmit={submitPickup}>
              <div className="pickup-panel__heading"><ClipboardCheck size={21} aria-hidden="true" /><div><h2>Verificación de identidad</h2><p>Completá los controles antes de confirmar la entrega.</p></div></div>
              <fieldset className="pickup-form__choices"><legend>¿Quién retira?</legend><label><input type="radio" name="pickup-type" checked={type === 'TITULAR'} onChange={() => setType('TITULAR')} /><UserRound size={20} aria-hidden="true" /> Destinatario</label><label><input type="radio" name="pickup-type" checked={type === 'TERCERO_AUTORIZADO'} onChange={() => setType('TERCERO_AUTORIZADO')} /><UsersRound size={20} aria-hidden="true" /> Tercero autorizado</label></fieldset>
              <p className="pickup-form__requirement">{type === 'TITULAR' ? packageInfo.requirements.recipient : packageInfo.requirements.authorizedPerson}</p>
              {type === 'TERCERO_AUTORIZADO' && <div className="form-field"><label htmlFor="pickup-authorized-name">Nombre completo de quien retira</label><input className="form-control" id="pickup-authorized-name" value={authorizedName} onChange={(event) => setAuthorizedName(event.target.value)} minLength={2} maxLength={150} required /></div>}
              <div className="pickup-form__grid">
                <div className="form-field"><label htmlFor="pickup-document-type">Tipo de documento presentado</label><select className="form-control" id="pickup-document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)} required><option value="DNI">DNI</option><option value="PASAPORTE">Pasaporte</option><option value="LC">LC</option><option value="LE">LE</option></select></div>
                <div className="form-field"><label htmlFor="pickup-document-number">Número de documento de quien retira</label><input className="form-control" id="pickup-document-number" value={documentNumber} onChange={(event) => setDocumentNumber(event.target.value)} maxLength={20} required /></div>
              </div>
              <div className="pickup-form__checks">
                <label><input type="checkbox" checked={recipientOver16} onChange={(event) => setRecipientOver16(event.target.checked)} /> <span>Verifiqué que el destinatario tiene al menos 16 años.</span></label>
                <label><input type="checkbox" checked={documentReviewed} onChange={(event) => setDocumentReviewed(event.target.checked)} /> <span><IdCard size={17} aria-hidden="true" /> Revisé el documento original de quien retira.</span></label>
                <label><input type="checkbox" checked={branchVerified} onChange={(event) => setBranchVerified(event.target.checked)} /> <span>Confirmé que el paquete está en la sucursal de retiro indicada.</span></label>
                {type === 'TERCERO_AUTORIZADO' && <><label><input type="checkbox" checked={hasRecipientDocumentCopy} onChange={(event) => setHasRecipientDocumentCopy(event.target.checked)} /> <span>Revisé la copia del documento del destinatario.</span></label><label><input type="checkbox" checked={hasSignedAuthorization} onChange={(event) => setHasSignedAuthorization(event.target.checked)} /> <span>Revisé la autorización de retiro firmada por el destinatario.</span></label></>}
              </div>
              <div className="form-field"><label htmlFor="pickup-notes">Observaciones <small>(opcional)</small></label><textarea className="form-control" id="pickup-notes" value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={500} rows={3} /></div>
              {registration.isError && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{registration.error.message}</p>}
              <button className="pickup-button" type="submit" disabled={!canRegister || registration.isPending}>{registration.isPending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <BadgeCheck size={18} aria-hidden="true" />}{registration.isPending ? 'Registrando…' : 'Confirmar retiro'}</button>
            </form>
          )}
        </>
      )}
    </main>
  )
}
