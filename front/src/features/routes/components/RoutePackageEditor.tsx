import { useState, type FormEvent } from 'react'
import { ArrowDown, ArrowUp, CircleAlert, LoaderCircle, Plus, Save, Trash2, X } from 'lucide-react'
import type { DeliveryRoute } from '../types/route.types'
import { orderedPackages } from '../routePresentation'

export function RoutePackageEditor({ route, busy, onSave, onCancel }: {
  route: DeliveryRoute
  busy: boolean
  onSave: (codes: string[]) => Promise<void>
  onCancel: () => void
}) {
  const original = orderedPackages(route)
  const [codes, setCodes] = useState(() => original.map((item) => item.code))
  const [newCode, setNewCode] = useState('')
  const [message, setMessage] = useState('')

  function move(index: number, change: number) {
    setCodes((current) => { const next = [...current]; [next[index], next[index + change]] = [next[index + change], next[index]]; return next })
  }

  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const code = newCode.trim().toUpperCase()
    if (!code) return
    if (codes.includes(code)) { setMessage('Ese paquete ya está en la lista.'); return }
    if (codes.length >= 500) { setMessage('Un recorrido admite hasta 500 paquetes.'); return }
    setCodes((current) => [...current, code]); setNewCode(''); setMessage('')
  }

  async function save() {
    if (busy || !codes.length) return
    setMessage('')
    try { await onSave(codes) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'No pudimos guardar los cambios.') }
  }

  return <section className="route-editor" aria-labelledby="route-editor-title">
    <h3 id="route-editor-title">Editar orden y paquetes</h3>
    <p className="route-hint">Usá las flechas para cambiar el orden de visita. Para mover un paquete a otro recorrido, quitalo, guardá y agregá su código al otro recorrido.</p>
    <ol className="route-editor__list">
      {codes.map((code, index) => {
        const item = original.find((entry) => entry.code === code)
        return <li key={code}><span className="route-stop-number">{index + 1}</span><div><strong>{code}</strong><p>{item ? `${item.description} · ${item.destination}` : 'Paquete agregado: se comprobará su disponibilidad al guardar.'}</p></div>
          <div className="route-editor__actions">
            <button className="route-icon-button" type="button" aria-label={`Subir paquete ${code}`} disabled={busy || index === 0} onClick={() => move(index, -1)}><ArrowUp size={17} aria-hidden="true" /></button>
            <button className="route-icon-button" type="button" aria-label={`Bajar paquete ${code}`} disabled={busy || index === codes.length - 1} onClick={() => move(index, 1)}><ArrowDown size={17} aria-hidden="true" /></button>
            <button className="route-icon-button route-button--danger" type="button" aria-label={`Quitar paquete ${code}`} disabled={busy} onClick={() => setCodes((current) => current.filter((entry) => entry !== code))}><Trash2 size={17} aria-hidden="true" /></button>
          </div>
        </li>
      })}
    </ol>
    {!codes.length && <p className="route-hint">El recorrido necesita al menos un paquete. Para descartarlo, cancelá esta edición y elegí «Eliminar recorrido».</p>}
    <form className="route-editor__add" onSubmit={add}>
      <div className="form-field"><label htmlFor="route-add-package">Agregar paquete por código</label><input id="route-add-package" className="form-control" value={newCode} onChange={(event) => setNewCode(event.target.value.toUpperCase())} placeholder="PAQ-XXXXXXXXXX" maxLength={40} autoComplete="off" disabled={busy} required /></div>
      <button className="route-button" type="submit" disabled={busy || !newCode.trim()}><Plus size={17} aria-hidden="true" /> Agregar</button>
    </form>
    {message && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{message}</p>}
    <div className="route-actions"><button className="route-button route-button--primary" type="button" disabled={busy || !codes.length} onClick={() => void save()}>{busy ? <LoaderCircle size={18} className="loading-icon" aria-hidden="true" /> : <Save size={18} aria-hidden="true" />} Guardar cambios</button><button className="route-button" type="button" disabled={busy} onClick={onCancel}><X size={18} aria-hidden="true" /> Cancelar edición</button></div>
  </section>
}
