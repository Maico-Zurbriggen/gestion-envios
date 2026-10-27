import { useState, type FormEvent } from 'react'
import { CheckCircle2, RefreshCw, ScanBarcode, Search } from 'lucide-react'
import { useBranches } from '../../shipments/hooks/useBranches'
import { useTerminal } from '../hooks/useTerminal'
import '../../../shared/styles/operations.css'

export function TerminalPage() {
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [branchId, setBranchId] = useState('')
  const [notes, setNotes] = useState('')
  const branches = useBranches()
  const { scan, receive } = useTerminal(code)
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalized = input.replace(/\s/g, '').toUpperCase()
    if (!normalized) return
    receive.reset(); setNotes('')
    if (normalized === code) void scan.refetch()
    else setCode(normalized)
  }
  const item = scan.data
  return <div className="ops-page">
    <header><h1><ScanBarcode size={28} aria-hidden="true" /> Recepción en terminal</h1><p>Leé el código de barras con el lector o ingresá el número del paquete. Revisá los datos antes de confirmar.</p></header>
    <form className="ops-panel ops-stack" onSubmit={search}>
      <label className="form-field" htmlFor="terminal-code">Código del paquete<input id="terminal-code" className="form-control" value={input} onChange={(e) => setInput(e.target.value)} required maxLength={80} autoComplete="off" disabled={receive.isPending} placeholder="PAQ-XXXXXXXXXX" /></label>
      <button className="ops-button" disabled={scan.isFetching || receive.isPending}><Search size={18} aria-hidden="true" />{scan.isFetching ? 'Consultando…' : 'Identificar paquete'}</button>
    </form>
    {scan.isFetching && <p role="status">Consultando el paquete…</p>}
    {scan.isError && <div className="form-error" role="alert">{scan.error.message}<button className="ops-button" type="button" disabled={scan.isFetching} onClick={() => void scan.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar</button></div>}
    {item && !scan.isError && <section className="ops-panel ops-stack" aria-label="Paquete identificado">
      <h2>{item.code}</h2><p><strong>{item.description}</strong> · {item.weightKg} kg · {item.dimensions}</p><p>Estado: {item.status}</p>
      <p>Remitente: {item.senderName} · Documento: {item.senderDocument}</p><p>Destinatario: {item.recipientName}</p><p>Destino: {item.destination}</p>{item.notes && <p>Observaciones declaradas: {item.notes}</p>}
      {!item.available && <p role="status">{item.unavailableReason || 'Este paquete no está disponible para recepción.'}</p>}
      {item.available && !receive.isSuccess && <form className="ops-stack" onSubmit={(e) => { e.preventDefault(); receive.mutate({ code: item.code, branchId: Number(branchId), notes }) }}>
        <fieldset className="ops-stack" disabled={receive.isPending || scan.isFetching}>
          <label className="form-field" htmlFor="terminal-branch">Sucursal donde recibís el paquete<select id="terminal-branch" className="form-control" value={branchId} onChange={(e) => setBranchId(e.target.value)} required><option value="">Seleccioná una sucursal</option>{branches.data?.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>
          {branches.isPending && <p role="status">Cargando sucursales…</p>}
          {branches.isError && <div role="alert"><p>{branches.error.message}</p><button className="ops-button" type="button" onClick={() => void branches.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar sucursales</button></div>}
          <label className="form-field" htmlFor="terminal-notes">Observaciones de recepción (opcional)<textarea id="terminal-notes" className="form-control" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} /></label>
          <button className="ops-button" disabled={!branchId || branches.isError || branches.isPending}><CheckCircle2 size={18} aria-hidden="true" />{receive.isPending ? 'Registrando…' : 'Confirmar recepción física'}</button>
        </fieldset>
      </form>}
    </section>}
    {receive.isError && <p className="form-error" role="alert">{receive.error.message} Revisá el estado actualizado antes de repetir la recepción.</p>}
    {receive.data && <div className="ops-success" role="status"><CheckCircle2 size={20} aria-hidden="true" /> {receive.data.code} recibido en {receive.data.branchName}. Estado: {receive.data.status}. {new Date(receive.data.receivedAt).toLocaleString('es-AR')}</div>}
  </div>
}
