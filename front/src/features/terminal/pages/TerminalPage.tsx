import { useRef, useState, type FormEvent } from 'react'
import { CheckCircle2, RefreshCw, ScanBarcode, Search } from 'lucide-react'
import { useBranches } from '../../shipments/hooks/useBranches'
import { ShipmentNotifications } from '../../notifications/components/ShipmentNotifications'
import { getStatusLabel } from '../../tracking/trackingStatus'
import { useTerminal } from '../hooks/useTerminal'
import type { ScannedPackage } from '../types/terminal.types'
import { ScanWithCameraButton } from '../../../shared/components/ScanWithCameraButton'
import { PACKAGE_CODE_PATTERN } from '../../../shared/services/scannedCode'
import { PrintLabelsButton } from '../../../shared/printing/PrintLabelsButton'
import type { ShipmentLabelData } from '../../../shared/printing/shipmentLabels'
import '../../../shared/styles/operations.css'

const BRANCH_STORAGE_KEY = 'terminal-branch'

// La sucursal es la misma durante todo el turno: se recuerda solo como comodidad local.
function readStoredBranch() {
  try { return localStorage.getItem(BRANCH_STORAGE_KEY) ?? '' } catch { return '' }
}

function storeBranch(value: string) {
  try { localStorage.setItem(BRANCH_STORAGE_KEY, value) } catch { /* almacenamiento no disponible */ }
}

// Reimpresión con los datos que ya trae la identificación: sin consultas extra.
function toPrintLabel(item: ScannedPackage): ShipmentLabelData {
  return {
    packageNumber: item.code,
    trackingToken: item.trackingToken,
    recipientName: item.recipientName,
    destination: item.destination,
    weightKg: item.weightKg,
    dimensions: item.dimensions,
    date: new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date()),
    dateCaption: 'Reimpreso',
  }
}

export function TerminalPage() {
  const codeInputRef = useRef<HTMLInputElement>(null)
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [branchId, setBranchId] = useState(readStoredBranch)
  const [notes, setNotes] = useState('')
  const branches = useBranches()
  const { scan, receive } = useTerminal(code)
  const branchExists = Boolean(branches.data?.some((branch) => String(branch.id) === branchId))

  function focusCode() {
    requestAnimationFrame(() => codeInputRef.current?.focus())
  }

  // Única entrada de códigos: el lector USB, el tipeo manual y la cámara terminan acá.
  function searchCode(value: string) {
    const normalized = value.replace(/\s/g, '').toUpperCase()
    if (!normalized) return
    receive.reset(); setNotes('')
    if (normalized === code) void scan.refetch()
    else setCode(normalized)
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    searchCode(input)
  }

  function searchFromCamera(scanned: string) {
    if (receive.isPending) return 'Esperá a que termine la recepción en curso antes de leer otro paquete.'
    setInput(scanned)
    searchCode(scanned)
  }

  function selectBranch(value: string) {
    setBranchId(value)
    storeBranch(value)
  }

  function nextPackage() {
    setInput(''); setCode(''); setNotes('')
    receive.reset()
    focusCode()
  }

  const item = scan.data
  return <div className="ops-page">
    <header className="ops-page__header"><span className="eyebrow"><ScanBarcode size={15} aria-hidden="true" /> Operación de terminal</span><h1>Recepción en terminal</h1><p>Leé el código de barras con el lector o ingresá el número del paquete. Revisá los datos antes de confirmar.</p></header>
    <form className="ops-panel ops-scan ops-scan--camera" onSubmit={search}>
      <label className="form-field" htmlFor="terminal-code">Código del paquete<input ref={codeInputRef} id="terminal-code" className="form-control" value={input} onChange={(e) => setInput(e.target.value)} onFocus={(e) => e.target.select()} required maxLength={80} autoComplete="off" autoFocus disabled={receive.isPending} placeholder="PAQ-XXXXXXXXXX" /></label>
      <button className="ops-button ops-button--primary" disabled={scan.isFetching || receive.isPending}><Search size={18} aria-hidden="true" />{scan.isFetching ? 'Consultando…' : 'Identificar paquete'}</button>
      <ScanWithCameraButton mode="continuous" pattern={PACKAGE_CODE_PATTERN} patternMessage={(read) => `${read} no es un código de paquete (PAQ-XXXXXXXXXX).`} onScan={searchFromCamera} disabled={receive.isPending}
        description="Apuntá la cámara trasera al código de barras de cada paquete. Cada lectura identifica el paquete automáticamente."
        continuousHint="Cerrá la cámara para revisar los datos del paquete y confirmar la recepción física." />
    </form>
    {scan.isFetching && <p role="status">Consultando el paquete…</p>}
    {scan.isError && <div className="form-error" role="alert">{scan.error.message}<button className="ops-button" type="button" disabled={scan.isFetching} onClick={() => void scan.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar</button></div>}
    {item && !scan.isError && <section className="ops-panel ops-stack" aria-label="Paquete identificado">
      <div className="ops-package__heading"><div><span className="eyebrow">Paquete identificado</span><h2>{item.code}</h2></div><span className="badge">{getStatusLabel(item.status)}</span></div>
      <dl className="ops-details">
        <div><dt>Contenido</dt><dd><strong>{item.description}</strong> · {item.weightKg} kg · {item.dimensions}</dd></div>
        <div><dt>Estado</dt><dd>{getStatusLabel(item.status)}</dd></div>
        <div><dt>Remitente</dt><dd>{item.senderName} · Documento: {item.senderDocument}</dd></div>
        <div><dt>Destinatario</dt><dd>{item.recipientName}</dd></div>
        <div className="ops-details__wide"><dt>Destino</dt><dd>{item.destination}</dd></div>
        {item.notes && <div className="ops-details__wide"><dt>Observaciones declaradas</dt><dd>{item.notes}</dd></div>}
      </dl>
      <div className="ops-actions"><PrintLabelsButton labels={[toPrintLabel(item)]} label="Reimprimir etiqueta" /></div>
      {!item.available && <p role="status">{item.unavailableReason || 'Este paquete no está disponible para recepción.'}</p>}
      {item.available && !receive.isSuccess && <form className="ops-stack" onSubmit={(e) => {
        e.preventDefault()
        receive.mutate({ code: item.code, branchId: Number(branchId), notes }, { onSuccess: () => { setInput(''); focusCode() } })
      }}>
        <fieldset className="ops-stack" disabled={receive.isPending || scan.isFetching}>
          <label className="form-field" htmlFor="terminal-branch">Sucursal donde recibís el paquete<select id="terminal-branch" className="form-control" value={branchExists ? branchId : ''} onChange={(e) => selectBranch(e.target.value)} required><option value="">Seleccioná una sucursal</option>{branches.data?.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>
          {branches.isPending && <p role="status">Cargando sucursales…</p>}
          {branches.isError && <div role="alert"><p>{branches.error.message}</p><button className="ops-button" type="button" onClick={() => void branches.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar sucursales</button></div>}
          <label className="form-field" htmlFor="terminal-notes">Observaciones de recepción (opcional)<textarea id="terminal-notes" className="form-control" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} /></label>
          <button className="ops-button ops-button--primary" disabled={!branchExists || branches.isError || branches.isPending}><CheckCircle2 size={18} aria-hidden="true" />{receive.isPending ? 'Registrando…' : 'Confirmar recepción física'}</button>
        </fieldset>
      </form>}
    </section>}
    {receive.isError && <p className="form-error" role="alert">{receive.error.message} Revisá el estado actualizado antes de repetir la recepción.</p>}
    {receive.data && <div className="ops-success ops-stack" role="status">
      <p><CheckCircle2 size={20} aria-hidden="true" /> {receive.data.code} recibido en {receive.data.branchName}. Estado: {getStatusLabel(receive.data.status)}. {new Date(receive.data.receivedAt).toLocaleString('es-AR')}</p>
      <p className="ops-hint">El campo de código quedó listo para escanear el siguiente paquete.</p>
      <div className="ops-actions"><button className="ops-button" type="button" onClick={nextPackage}><ScanBarcode size={18} aria-hidden="true" /> Procesar otro paquete</button></div>
    </div>}
    {item && !scan.isError && <ShipmentNotifications key={item.trackingToken} trackingToken={item.trackingToken} />}
  </div>
}
