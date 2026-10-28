import { useRef, useState, type FormEvent } from 'react'
import { CheckCircle2, CircleAlert, Printer, RefreshCw, ScanBarcode, Search, Weight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { TraceLink } from '../../monitor/components/TraceLink'
import { useBranches } from '../../shipments/hooks/useBranches'
import { ShipmentNotifications } from '../../notifications/components/ShipmentNotifications'
import { getStatusLabel } from '../../tracking/trackingStatus'
import { useTerminal } from '../hooks/useTerminal'
import type { ScannedPackage } from '../types/terminal.types'
import { ScanWithCameraButton } from '../../../shared/components/ScanWithCameraButton'
import { PACKAGE_CODE_PATTERN } from '../../../shared/services/scannedCode'
import { PrintLabelsButton } from '../../../shared/printing/PrintLabelsButton'
import { printShipmentLabels } from '../../../shared/printing/printLabels'
import type { ShipmentLabelData } from '../../../shared/printing/shipmentLabels'
import { usePrintSettings } from '../../../shared/printing/usePrintSettings'
import { showToast } from '../../../shared/services/toast'
import '../../../shared/styles/operations.css'
import { formatLongDay } from '../../../shared/utils/dates'

const BRANCH_STORAGE_KEY = 'terminal-branch'

// La sucursal es la misma durante todo el turno: se recuerda solo como comodidad local.
function readStoredBranch() {
  try { return localStorage.getItem(BRANCH_STORAGE_KEY) ?? '' } catch { return '' }
}

function storeBranch(value: string) {
  try { localStorage.setItem(BRANCH_STORAGE_KEY, value) } catch { /* almacenamiento no disponible */ }
}

const AUTO_PRINT_KEY = 'terminal-imprimir-al-admitir'

function readAutoPrint() {
  try { return localStorage.getItem(AUTO_PRINT_KEY) !== '0' } catch { return true }
}

function storeAutoPrint(value: boolean) {
  try { localStorage.setItem(AUTO_PRINT_KEY, value ? '1' : '0') } catch { /* almacenamiento no disponible */ }
}

// Etiqueta con los datos que ya trae la identificación: sin consultas extra.
function toPrintLabel(item: ScannedPackage, caption: string, weightKg?: number | null): ShipmentLabelData {
  return {
    packageNumber: item.code,
    trackingToken: item.trackingToken,
    recipientName: item.recipientName,
    destination: item.destination,
    deliveryType: item.deliveryType,
    weightKg: weightKg ?? item.weightKg,
    dimensions: item.dimensions,
    index: item.packageIndex,
    total: item.packageTotal,
    date: new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date()),
    dateCaption: caption,
  }
}

export function TerminalPage() {
  const codeInputRef = useRef<HTMLInputElement>(null)
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [branchId, setBranchId] = useState(readStoredBranch)
  const [notes, setNotes] = useState('')
  const [scaleWeight, setScaleWeight] = useState('')
  const [autoPrint, setAutoPrint] = useState(readAutoPrint)
  const [printSettings] = usePrintSettings()
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
    receive.reset(); setNotes(''); setScaleWeight('')
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
    setInput(''); setCode(''); setNotes(''); setScaleWeight('')
    receive.reset()
    focusCode()
  }

  const item = scan.data
  return <div className="ops-page">
    <header className="ops-page__header"><span className="eyebrow"><ScanBarcode size={15} aria-hidden="true" /> Operación de terminal</span><h1>Recepción en terminal</h1><p>Admisión del paquete: leé el código del comprobante del cliente, revisá los datos, pesalo y confirmá. Al confirmar se imprime la etiqueta para pegar en la caja.</p><p className="ops-hint">¿Llega un recorrido de otra sucursal? Controlá lo que baja en <Link to="/terminal/descarga">Carga y descarga</Link>.</p></header>
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
      <div className="ops-actions"><PrintLabelsButton labels={[toPrintLabel(item, item.available ? 'Admitido' : 'Reimpreso')]} label={item.available ? 'Imprimir etiqueta' : 'Reimprimir etiqueta'} /><TraceLink code={item.code} className="ops-button" /></div>
      {!item.available && <p role="status">{item.unavailableReason || 'Este paquete no está disponible para recepción.'}</p>}
      {item.available && !receive.isSuccess && <form className="ops-stack" onSubmit={(e) => {
        e.preventDefault()
        const weight = Number(scaleWeight.replace(',', '.'))
        receive.mutate({ code: item.code, branchId: Number(branchId), notes, scaleWeightKg: weight > 0 ? weight : null }, {
          onSuccess: (reception) => {
            setInput('')
            // Admisión: la etiqueta se imprime y se pega en la caja en el mostrador.
            if (autoPrint) {
              try {
                printShipmentLabels([toPrintLabel(item, 'Admitido', reception.scaleWeightKg)], printSettings)
              } catch {
                showToast('No pudimos abrir la impresión. Usá «Imprimir etiqueta».', 'error')
              }
            }
            focusCode()
          },
        })
      }}>
        <fieldset className="ops-stack" disabled={receive.isPending || scan.isFetching}>
          <label className="form-field" htmlFor="terminal-branch">Sucursal donde recibís el paquete<select id="terminal-branch" className="form-control" value={branchExists ? branchId : ''} onChange={(e) => selectBranch(e.target.value)} required><option value="">Seleccioná una sucursal</option>{branches.data?.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>
          {branches.isPending && <p role="status">Cargando sucursales…</p>}
          {branches.isError && <div role="alert"><p>{branches.error.message}</p><button className="ops-button" type="button" onClick={() => void branches.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar sucursales</button></div>}
          <label className="form-field" htmlFor="terminal-weight">Peso en balanza (kg, opcional)
            <span className="ops-input-icon"><Weight size={17} aria-hidden="true" /><input id="terminal-weight" className="form-control" type="text" inputMode="decimal" placeholder={`Declarado: ${item.weightKg} kg`} value={scaleWeight} onChange={(e) => setScaleWeight(e.target.value.replace(/[^\d.,]/g, ''))} /></span>
          </label>
          <label className="form-field" htmlFor="terminal-notes">Observaciones de recepción (opcional)<textarea id="terminal-notes" className="form-control" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} /></label>
          <label className="ops-check" htmlFor="terminal-autoprint"><input id="terminal-autoprint" type="checkbox" checked={autoPrint} onChange={(e) => { setAutoPrint(e.target.checked); storeAutoPrint(e.target.checked) }} /> <Printer size={16} aria-hidden="true" /> Imprimir la etiqueta al confirmar (para pegarla en la caja)</label>
          <button className="ops-button ops-button--primary" disabled={!branchExists || branches.isError || branches.isPending}><CheckCircle2 size={18} aria-hidden="true" />{receive.isPending ? 'Registrando…' : 'Confirmar recepción física'}</button>
        </fieldset>
      </form>}
    </section>}
    {receive.isError && <p className="form-error" role="alert">{receive.error.message} Revisá el estado actualizado antes de repetir la recepción.</p>}
    {receive.data && <div className="ops-success ops-stack" role="status">
      <p><CheckCircle2 size={20} aria-hidden="true" /> {receive.data.code} recibido en {receive.data.branchName}. Estado: {getStatusLabel(receive.data.status)}. {new Date(receive.data.receivedAt).toLocaleString('es-AR')}</p>
      {receive.data.weightWarning && <p className="ops-warning"><CircleAlert size={18} aria-hidden="true" /> {receive.data.weightWarning}</p>}
      {receive.data.pickupUntil && <p className="ops-hint">Es la sucursal de retiro: queda para el destinatario hasta el {formatLongDay(receive.data.pickupUntil)}. Ya le avisamos.</p>}
      <p className="ops-hint">Le avisamos al remitente que recibimos el paquete.</p>
      <p className="ops-hint">El campo de código quedó listo para escanear el siguiente paquete.</p>
      <div className="ops-actions"><button className="ops-button" type="button" onClick={nextPackage}><ScanBarcode size={18} aria-hidden="true" /> Procesar otro paquete</button></div>
    </div>}
    {item && !scan.isError && <ShipmentNotifications key={item.trackingToken} trackingToken={item.trackingToken} />}
  </div>
}
