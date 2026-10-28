import { useState } from 'react'
import { CircleAlert, MapPinOff, PackageSearch, RotateCcw, Search, Undo2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { PendingPackage } from '../types/route.types'

type Filter = 'todos' | 'ubicados' | 'sinUbicacion'

/** Lista de paquetes que esperan recorrido, para elegir cuáles se suman. */
export function PendingPackagesPicker({ packages, selected, onChange, disabled = false }: {
  packages: PendingPackage[]
  selected: Set<string>
  onChange: (next: Set<string>) => void
  disabled?: boolean
}) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('todos')
  const located = packages.filter((item) => item.located)
  const query = search.trim().toLowerCase()
  const visible = packages.filter((item) =>
    (filter === 'todos' || (filter === 'ubicados') === item.located)
    && (!query || [item.code, item.recipientName, item.destination, item.description].some((text) => text.toLowerCase().includes(query))))
  const allVisibleSelected = visible.length > 0 && visible.every((item) => selected.has(item.code))

  function toggle(code: string) {
    const next = new Set(selected)
    if (next.has(code)) next.delete(code)
    else next.add(code)
    onChange(next)
  }

  function toggleVisible() {
    const next = new Set(selected)
    for (const item of visible) {
      if (allVisibleSelected) next.delete(item.code)
      else next.add(item.code)
    }
    onChange(next)
  }

  if (!packages.length) {
    return <div className="route-empty"><PackageSearch size={20} aria-hidden="true" /><p>
      <strong>No hay paquetes esperando en esta sucursal.</strong><br />
      Un envío registrado aparece acá cuando se recibe en la sucursal desde <Link to="/terminal/recepcion">Recibir paquetes</Link>.
    </p></div>
  }

  return <div className="route-picker">
    <div className="route-picker__tools">
      <label className="route-picker__search">
        <Search size={16} aria-hidden="true" />
        <span className="visually-hidden">Buscar paquetes en espera</span>
        <input className="form-control" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Paquete, destinatario o dirección" disabled={disabled} />
      </label>
      <div className="segmented" role="group" aria-label="Filtrar por ubicación">
        <button type="button" aria-pressed={filter === 'todos'} onClick={() => setFilter('todos')}>Todos {packages.length}</button>
        <button type="button" aria-pressed={filter === 'ubicados'} onClick={() => setFilter('ubicados')}>Ubicados {located.length}</button>
        {located.length < packages.length && <button type="button" aria-pressed={filter === 'sinUbicacion'} onClick={() => setFilter('sinUbicacion')}>Sin ubicación {packages.length - located.length}</button>}
      </div>
      <button className="route-button route-picker__all" type="button" onClick={toggleVisible} disabled={disabled || !visible.length}>
        {allVisibleSelected ? 'Quitar selección' : `Elegir ${visible.length === 1 ? 'el visible' : `los ${visible.length}`}`}
      </button>
    </div>
    {visible.length === 0
      ? <p className="route-hint">Ningún paquete coincide con la búsqueda.</p>
      : <ul className="route-picker__list">
        {visible.map((item) => <li key={item.code}>
          <label className={`route-picker__item${selected.has(item.code) ? ' is-selected' : ''}`}>
            <input type="checkbox" checked={selected.has(item.code)} onChange={() => toggle(item.code)} disabled={disabled} />
            <span className="route-picker__text">
              <strong>{item.recipientName}</strong>
              <small>{item.destination}</small>
              <span className="route-picker__meta">
                <span className="route-code">{item.code}</span>
                <span>{item.description} · {item.weightKg} kg</span>
              </span>
              {(item.issue || item.previousVisits > 0 || item.isReturn) && <span className="route-picker__badges">
                {item.issue && <span className="badge badge--warning">{item.located ? <CircleAlert size={13} aria-hidden="true" /> : <MapPinOff size={13} aria-hidden="true" />}{item.issue}</span>}
                {item.previousVisits > 0 && <span className="badge badge--info"><RotateCcw size={13} aria-hidden="true" />{item.previousVisits + 1}.ª visita</span>}
                {item.isReturn && <span className="badge badge--info"><Undo2 size={13} aria-hidden="true" />Devolución</span>}
              </span>}
            </span>
          </label>
        </li>)}
      </ul>}
  </div>
}
