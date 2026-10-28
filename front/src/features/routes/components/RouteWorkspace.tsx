import { useState, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowDown, ArrowLeft, ArrowUp, Check, CircleAlert, ClipboardCheck, GripVertical, MapPin, MapPinOff, Package, Play, Plus,
  RotateCcw, Trash2, Undo2, UserRound, WandSparkles, X,
} from 'lucide-react'
import { TraceLink } from '../../monitor/components/TraceLink'
import { useRoute, useRouteCommand, usePendingPackages } from '../hooks/useRoutes'
import { useRoadRoute } from '../hooks/useRoadRoute'
import { dayParts, distanceLabels, formatRouteDistance, formatRouteDuration, isRouteEditable, routeStatusLabels, routeStatusTone } from '../routePresentation'
import type { DeliveryRoute, Driver, RouteCommand, RouteStop } from '../types/route.types'
import { ConfirmRouteAction } from './ConfirmRouteAction'
import { DeliveryRouteMap } from './DeliveryRouteMap'
import { PendingPackagesPicker } from './PendingPackagesPicker'
import { RouteError, RouteLoading } from './RouteFeedback'
import { RouteLocationEditor } from './RouteLocationEditor'

type Confirm = 'start' | 'delete' | null
type Side = 'map' | 'add' | { locate: RouteStop }

/** Códigos en el orden de visita: el orden de las paradas y, dentro de cada una, el de sus paquetes. */
function codesOf(stops: RouteStop[]) {
  return stops.flatMap((stop) => [...stop.packages].sort((a, b) => a.order - b.order).map((item) => item.code))
}

function moveTo<T>(list: T[], from: number, to: number) {
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

/** Espacio de trabajo de un recorrido: encabezado con el próximo paso, paradas a la izquierda y mapa (o paquetes para sumar) a la derecha. */
export function RouteWorkspace({ id, drivers, busyDriverIds, onBack, onDeleted }: {
  id: string
  /** Repartidores aptos para este recorrido (sucursal y tipo). */
  drivers: Driver[]
  busyDriverIds: Set<string>
  onBack: () => void
  onDeleted: () => void
}) {
  const query = useRoute(id)
  const command = useRouteCommand()
  const route = query.data
  const routing = useRoadRoute(route)
  const [confirm, setConfirm] = useState<Confirm>(null)
  const [side, setSide] = useState<Side>('map')
  const [notice, setNotice] = useState('')
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [overIndex, setOverIndex] = useState<number | null>(null)
  const [changingDriver, setChangingDriver] = useState(false)

  if (query.isPending) return <RouteLoading label="Cargando el recorrido…" />
  if (query.isError) return <div className="route-workspace"><button className="route-button" type="button" onClick={onBack}><ArrowLeft size={17} aria-hidden="true" /> Volver a los recorridos</button><RouteError error={query.error} onRetry={() => void query.refetch()} pending={query.isFetching} /></div>
  if (!route) return null

  const editable = isRouteEditable(route.status)
  const busy = command.isPending
  const stops = route.stops
  const total = route.packageCount
  const delivered = stops.flatMap((s) => s.packages).filter((p) => p.routeStatus === 'ENTREGADO').length
  const failed = stops.flatMap((s) => s.packages).filter((p) => p.routeStatus === 'FALLIDO').length
  const unlocated = stops.filter((s) => s.latitude == null || s.longitude == null).length
  const day = dayParts(route.date)

  function run(next: RouteCommand, done?: (message: string) => void) {
    setNotice('')
    command.mutate(next, {
      onSuccess: (result) => {
        setConfirm(null)
        if (next.action === 'delete') onDeleted()
        else (done ?? setNotice)(result.message)
      },
      onError: () => setConfirm(null),
    })
  }

  function saveOrder(nextStops: RouteStop[]) {
    run({ id, action: 'save', packages: codesOf(nextStops) }, () => setNotice('Orden actualizado.'))
  }

  function removePackage(code: string) {
    run({ id, action: 'save', packages: codesOf(stops).filter((item) => item !== code) }, () => setNotice(`${code} salió del recorrido y volvió a la lista de espera.`))
  }

  function onDrop(event: DragEvent, target: number) {
    event.preventDefault()
    const from = dragIndex
    setDragIndex(null); setOverIndex(null)
    if (from === null || from === target) return
    saveOrder(moveTo(stops, from, target))
  }

  return <section className="route-workspace" aria-labelledby="route-workspace-title">
    <div className="route-workspace__top">
      <button className="btn btn--ghost" type="button" onClick={onBack}><ArrowLeft size={17} aria-hidden="true" /> Recorridos del día</button>
    </div>

    <header className="surface-card route-head">
      <div className="route-head__main">
        <span className="route-avatar" aria-hidden="true">{initials(route.driver.name)}</span>
        <div className="route-head__titles">
          <h2 id="route-workspace-title">{route.driver.name} <span className={`badge ${routeStatusTone[route.status]}`}>{routeStatusLabels[route.status]}</span></h2>
          <p><span className="route-head__day">{day.long}</span> · {route.branchName} · {distanceLabels[route.distanceType]}</p>
        </div>
        <div className="route-head__actions">
          {editable && <>
            <button className="btn btn--primary" type="button" disabled={busy || !total} onClick={() => setConfirm('start')}><Play size={17} aria-hidden="true" /> Iniciar recorrido</button>
            <button className="btn btn--ghost" type="button" disabled={busy} onClick={() => setChangingDriver((value) => !value)} aria-expanded={changingDriver}><UserRound size={17} aria-hidden="true" /> Cambiar repartidor</button>
            <button className="btn btn--ghost route-head__danger" type="button" disabled={busy} onClick={() => setConfirm('delete')}><Trash2 size={17} aria-hidden="true" /> Eliminar</button>
          </>}
        </div>
      </div>
      {editable && <p className="route-head__hint">Normalmente lo inicia el repartidor desde su app al salir de la sucursal.</p>}

      {changingDriver && editable && <ChangeDriver route={route} drivers={drivers} busyDriverIds={busyDriverIds} busy={busy}
        onCancel={() => setChangingDriver(false)} onSave={(driverId) => run({ id, action: 'assign', driverId }, (message) => { setChangingDriver(false); setNotice(message) })} />}

      <dl className="route-head__metrics">
        <div><dt>Paquetes</dt><dd>{total}</dd><small>{stops.length} {stops.length === 1 ? 'parada' : 'paradas'}</small></div>
        <div><dt>Avance</dt><dd>{delivered}/{total}</dd><small>{failed ? `${failed} sin entregar` : route.status === 'FINALIZADO' ? 'Recorrido cerrado' : `${total - delivered - failed} pendientes`}</small></div>
        <div><dt>Distancia</dt><dd>{routing.data ? formatRouteDistance(routing.data.distanceMeters / 1000) : formatRouteDistance(route.distanceKm)}</dd><small>{routing.data ? 'por calles' : 'estimada'}</small></div>
        <div><dt>Tiempo</dt><dd>{routing.data ? formatRouteDuration(Math.ceil(routing.data.durationSeconds / 60)) : formatRouteDuration(route.durationMinutes)}</dd><small>de manejo</small></div>
      </dl>

      {editable && <div className="route-checklist" aria-label="Qué falta para salir">
        <span className="route-checklist__title">Antes de salir</span>
        <ChecklistItem ok icon={UserRound} label="Repartidor asignado" />
        <ChecklistItem ok={total > 0} icon={Package} label={total ? `${total} ${total === 1 ? 'paquete' : 'paquetes'}` : 'Sin paquetes'} />
        <ChecklistItem ok={unlocated === 0} warn icon={MapPin} label={unlocated ? `${unlocated} ${unlocated === 1 ? 'parada sin ubicación' : 'paradas sin ubicación'}` : 'Todas ubicadas en el mapa'} />
        <ChecklistItem ok={route.loadControl?.status === 'CERRADO'} optional icon={ClipboardCheck}
          label={route.loadControl ? route.loadControl.status === 'CERRADO' ? `Carga controlada (${route.loadControl.verified} de ${route.loadControl.expected})` : 'Controlando la carga' : 'Carga sin controlar'}
          link={route.loadControl?.status === 'CERRADO' ? undefined : { label: 'Controlar', to: '/terminal/descarga?modo=carga' }} />
      </div>}
    </header>

    {notice && <p className="route-success" role="status"><Check size={18} aria-hidden="true" />{notice}</p>}
    {command.isError && <RouteError error={command.error} />}

    <div className="route-board">
      <section className="surface-card route-stops-panel" aria-labelledby="route-stops-title">
        <header className="route-stops-panel__head">
          <h3 id="route-stops-title">Paradas <span className="badge badge--muted">{stops.length}</span></h3>
          {editable && stops.length > 1 && <button className="route-button" type="button" disabled={busy} onClick={() => run({ id, action: 'optimize' })} title="Ordena las paradas para que el recorrido tarde lo menos posible">
            <WandSparkles size={16} aria-hidden="true" /> Optimizar
          </button>}
          {editable && <button className={`route-button${side === 'add' ? ' route-button--primary' : ''}`} type="button" aria-pressed={side === 'add'} onClick={() => setSide(side === 'add' ? 'map' : 'add')}>
            <Plus size={16} aria-hidden="true" /> Agregar
          </button>}
        </header>
        {editable && stops.length > 1 && <p className="route-hint route-stops-panel__help">Arrastrá <GripVertical size={14} aria-label="el asa" /> o usá las flechas para cambiar el orden. Se guarda solo.</p>}
        {stops.length === 0
          ? <p className="route-empty"><Package size={20} aria-hidden="true" /> El recorrido no tiene paquetes. Tocá «Agregar» para sumar los que esperan.</p>
          : <ol className="route-stop-list">
            {stops.map((stop, index) => <li key={`${stop.order}-${stop.destination}`}
              className={`route-stop${dragIndex === index ? ' is-dragging' : ''}${overIndex === index && dragIndex !== null && dragIndex !== index ? ' is-drop-target' : ''}`}
              draggable={editable && !busy && stops.length > 1}
              onDragStart={(event) => { setDragIndex(index); event.dataTransfer.effectAllowed = 'move' }}
              onDragEnd={() => { setDragIndex(null); setOverIndex(null) }}
              onDragOver={(event) => { if (dragIndex !== null) { event.preventDefault(); setOverIndex(index) } }}
              onDrop={(event) => onDrop(event, index)}>
              <div className="route-stop__head">
                {editable && stops.length > 1 && <GripVertical className="route-stop__grip" size={16} aria-hidden="true" />}
                <span className="route-stop-number">{index + 1}</span>
                <div className="route-stop__place">
                  <strong>{stop.destination}</strong>
                  <small>{stop.type === 'SUCURSAL' ? 'Sucursal de destino' : 'Domicilio'}{stop.packages.length > 1 ? ` · ${stop.packages.length} paquetes` : ''}</small>
                </div>
                {editable && <div className="route-stop__order">
                  <button className="icon-action" type="button" aria-label={`Subir la parada ${index + 1}`} title="Subir" disabled={busy || index === 0} onClick={() => saveOrder(moveTo(stops, index, index - 1))}><ArrowUp size={16} aria-hidden="true" /></button>
                  <button className="icon-action" type="button" aria-label={`Bajar la parada ${index + 1}`} title="Bajar" disabled={busy || index === stops.length - 1} onClick={() => saveOrder(moveTo(stops, index, index + 1))}><ArrowDown size={16} aria-hidden="true" /></button>
                </div>}
              </div>
              {(stop.latitude == null || stop.longitude == null) && <p className="route-stop__warn">
                <MapPinOff size={14} aria-hidden="true" /> Sin ubicación en el mapa
                {editable && stop.type === 'DOMICILIO' && <button className="route-link" type="button" disabled={busy} onClick={() => setSide({ locate: stop })}>Ubicar domicilio</button>}
              </p>}
              <ul className="route-stop__packages">
                {stop.packages.map((item) => <li key={item.id}>
                  <span className={`route-stop__state route-stop__state--${item.routeStatus.toLowerCase()}`} aria-hidden="true">
                    {item.routeStatus === 'ENTREGADO' ? <Check size={12} /> : item.routeStatus === 'FALLIDO' ? <X size={12} /> : null}
                  </span>
                  <span className="route-stop__package">
                    <span><strong>{item.recipientName}</strong> <span className="route-code">{item.code}</span></span>
                    <small>{item.description} · {item.weightKg} kg{item.routeStatus === 'ENTREGADO' ? ' · Entregado' : item.routeStatus === 'FALLIDO' ? ' · Sin entregar' : ''}</small>
                    {((item.previousVisits > 0 && item.routeStatus === 'PENDIENTE') || item.isReturn) && <span className="route-picker__badges">
                      {item.previousVisits > 0 && item.routeStatus === 'PENDIENTE' && <span className="badge badge--warning"><RotateCcw size={12} aria-hidden="true" />{item.previousVisits + 1}.ª de {route.maxVisits} visitas</span>}
                      {item.isReturn && <span className="badge badge--info"><Undo2 size={12} aria-hidden="true" />Devolución</span>}
                    </span>}
                  </span>
                  <span className="route-stop__links">
                    <TraceLink code={item.code} className="icon-action" label="" />
                    {editable && <button className="icon-action icon-action--danger" type="button" disabled={busy || total === 1} onClick={() => removePackage(item.code)}
                      aria-label={`Quitar ${item.code} del recorrido`} title={total === 1 ? 'Es el único paquete: para vaciarlo, eliminá el recorrido' : 'Quitar del recorrido (vuelve a la lista de espera)'}>
                      <Trash2 size={15} aria-hidden="true" />
                    </button>}
                  </span>
                </li>)}
              </ul>
            </li>)}
          </ol>}
      </section>

      <div className="route-side">
        {typeof side === 'object' && editable
          ? <RouteLocationEditor route={route} stop={side.locate} busy={busy} onCancel={() => setSide('map')}
            onSave={async (latitude, longitude) => {
              const result = await command.mutateAsync({ id, action: 'locate', packageCode: side.locate.packages[0].code, latitude, longitude })
              setNotice(result.message); setSide('map')
            }} />
          : side === 'add' && editable
            ? <AddPackages route={route} busy={busy} onClose={() => setSide('map')}
              onAdd={(codes) => run({ id, action: 'save', packages: [...codesOf(stops), ...codes] }, () => setNotice(`Se sumaron ${codes.length} ${codes.length === 1 ? 'paquete' : 'paquetes'} al final del recorrido.`))} />
            : <div className="surface-card route-map-card"><DeliveryRouteMap route={route} routing={routing} /></div>}
      </div>
    </div>

    {confirm && <ConfirmRouteAction
      title={confirm === 'start' ? '¿Iniciar el recorrido?' : '¿Eliminar el recorrido?'}
      description={confirm === 'start'
        ? 'Los paquetes salen de la sucursal y el cambio se ve en el seguimiento. Después ya no se puede editar.'
        : 'Sus paquetes vuelven a la lista de espera para sumarlos a otro recorrido.'}
      confirmLabel={confirm === 'start' ? 'Iniciar recorrido' : 'Eliminar recorrido'} pending={busy}
      onCancel={() => setConfirm(null)} onConfirm={() => run({ id, action: confirm })} />}
  </section>
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
}

function ChecklistItem({ ok, warn, optional, icon: Icon, label, link }: {
  ok: boolean; warn?: boolean; optional?: boolean; icon: typeof UserRound; label: string; link?: { label: string; to: string }
}) {
  const tone = ok ? 'ok' : optional ? 'optional' : warn ? 'warn' : 'missing'
  return <span className={`route-chip route-chip--${tone}`}>
    {ok ? <Check size={14} aria-hidden="true" /> : warn && !optional ? <CircleAlert size={14} aria-hidden="true" /> : <Icon size={14} aria-hidden="true" />}
    {label}
    {link && <Link to={link.to}>{link.label}</Link>}
  </span>
}

/** Cambia el repartidor por otro libre de la misma sucursal y tipo. */
function ChangeDriver({ route, drivers, busyDriverIds, busy, onCancel, onSave }: {
  route: DeliveryRoute; drivers: Driver[]; busyDriverIds: Set<string>; busy: boolean; onCancel: () => void; onSave: (driverId: string) => void
}) {
  const [driverId, setDriverId] = useState('')
  const options = drivers.filter((driver) => driver.id !== route.driver.id)
  return <form className="route-change-driver" onSubmit={(event) => { event.preventDefault(); if (driverId) onSave(driverId) }}>
    <div className="form-field">
      <label htmlFor="route-new-driver">Nuevo repartidor</label>
      <select id="route-new-driver" className="form-control" value={driverId} onChange={(event) => setDriverId(event.target.value)} required disabled={busy}>
        <option value="">Elegí un repartidor</option>
        {options.map((driver) => <option key={driver.id} value={driver.id} disabled={busyDriverIds.has(driver.id)}>{driver.name}{busyDriverIds.has(driver.id) ? ' · ya tiene recorrido ese día' : ''}</option>)}
      </select>
    </div>
    <button className="route-button route-button--primary" type="submit" disabled={busy || !driverId}>Cambiar</button>
    <button className="route-button" type="button" onClick={onCancel} disabled={busy}>Cancelar</button>
  </form>
}

/** Paquetes que esperan recorrido en la sucursal, para sumarlos al final de este. */
function AddPackages({ route, busy, onAdd, onClose }: { route: DeliveryRoute; busy: boolean; onAdd: (codes: string[]) => void; onClose: () => void }) {
  const pending = usePendingPackages(route.branchId, route.distanceType)
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const codes = (pending.data ?? []).filter((item) => selected.has(item.code)).map((item) => item.code)
  return <section className="surface-card route-add" aria-labelledby="route-add-title">
    <header className="route-add__head">
      <div><h3 id="route-add-title">Sumar paquetes</h3><p className="route-hint">Listos en {route.branchName} y sin recorrido. Se agregan al final; después podés optimizar.</p></div>
      <button className="icon-action" type="button" aria-label="Cerrar y volver al mapa" onClick={onClose}><X size={17} aria-hidden="true" /></button>
    </header>
    {pending.isPending && <RouteLoading label="Buscando paquetes en espera…" />}
    {pending.isError && <RouteError error={pending.error} onRetry={() => void pending.refetch()} pending={pending.isFetching} />}
    {pending.data && <PendingPackagesPicker packages={pending.data} selected={selected} onChange={setSelected} disabled={busy} />}
    {pending.data && pending.data.length > 0 && <footer className="route-add__foot">
      <button className="route-button route-button--primary" type="button" disabled={busy || !codes.length} onClick={() => { onAdd(codes); setSelected(new Set()) }}>
        <Plus size={16} aria-hidden="true" /> {codes.length ? `Sumar ${codes.length} al recorrido` : 'Elegí paquetes para sumar'}
      </button>
    </footer>}
  </section>
}
