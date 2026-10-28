import { useState, type FormEvent } from 'react'
import { CheckCircle2, CircleAlert, MapPin, Pencil, Play, RefreshCw, Route, Trash2, UserRound, WandSparkles } from 'lucide-react'
import { TraceLink } from '../../monitor/components/TraceLink'
import { Link } from 'react-router-dom'
import { useRoute, useRouteCommand } from '../hooks/useRoutes'
import { useRoadRoute } from '../hooks/useRoadRoute'
import { distanceLabels, formatRouteDistance, formatRouteDuration, isRouteEditable, routeStatusLabels } from '../routePresentation'
import type { Driver, RouteCommand, RouteStop } from '../types/route.types'
import { ConfirmRouteAction } from './ConfirmRouteAction'
import { DeliveryRouteMap } from './DeliveryRouteMap'
import { RouteError, RouteLoading } from './RouteFeedback'
import { RoutePackageEditor } from './RoutePackageEditor'
import { RouteLocationEditor } from './RouteLocationEditor'

export function DeliveryRouteDetail({ id, drivers, busy, editing, onEditingChange, onDeleted }: {
  id: string
  drivers: Driver[]
  busy: boolean
  editing: boolean
  onEditingChange: (value: boolean) => void
  onDeleted: () => void
}) {
  const query = useRoute(id)
  const mutation = useRouteCommand()
  const [driverId, setDriverId] = useState('')
  const [confirmation, setConfirmation] = useState<'start' | 'delete' | null>(null)
  const [notice, setNotice] = useState('')
  const [locationStop, setLocationStop] = useState<RouteStop | null>(null)
  const route = query.data
  const routing = useRoadRoute(route)
  const editable = route && isRouteEditable(route.status)
  const candidates = drivers.filter((driver) => driver.available && driver.branch?.id === route?.branchId && driver.distanceType === route?.distanceType)

  function execute(command: RouteCommand) {
    setNotice('')
    mutation.mutate(command, { onSuccess: (result) => {
      setConfirmation(null); setNotice(result.message)
      if (command.action === 'delete') onDeleted()
      if (command.action === 'assign') setDriverId('')
    }, onError: () => setConfirmation(null) })
  }

  async function save(codes: string[]) {
    const result = await mutation.mutateAsync({ id, action: 'save', packages: codes })
    setNotice(result.message)
    onEditingChange(false)
  }

  function cancelEditing() {
    setLocationStop(null)
    onEditingChange(false)
    mutation.reset()
  }

  async function saveLocation(latitude: number, longitude: number) {
    if (!locationStop) return
    const result = await mutation.mutateAsync({ id, action: 'locate', packageCode: locationStop.packages[0].code, latitude, longitude })
    setNotice(result.message)
    setLocationStop(null)
    onEditingChange(false)
  }

  function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!busy && driverId && driverId !== route?.driver.id) execute({ id, action: 'assign', driverId })
  }

  if (query.isPending) return <RouteLoading label="Cargando el recorrido y sus paradas…" />
  if (query.isError) return <div><RouteError error={query.error} onRetry={() => void query.refetch()} pending={query.isFetching} />{editing && <button className="route-button" type="button" disabled={busy} onClick={cancelEditing}>Salir de edición</button>}</div>
  if (!route) return null

  return <section className="route-panel route-detail" aria-labelledby="route-detail-title">
    <header className="route-detail__header"><div><span className="eyebrow">Recorrido {route.id.slice(0, 8)}</span><h2 id="route-detail-title">Recorrido de {route.driver.name}</h2><p>{route.branchName} · {distanceLabels[route.distanceType]} · {route.date}</p></div><span className="route-status">{routeStatusLabels[route.status]}</span></header>
    <dl className="route-stats"><div><dt>Paquetes</dt><dd>{route.packageCount}</dd></div><div><dt>Paradas</dt><dd>{route.stopCount}</dd></div><div><dt>Distancia por calles{routing.missingStops > 0 ? ' (parcial)' : ''}</dt><dd>{routing.data ? formatRouteDistance(routing.data.distanceMeters / 1000) : routing.loading ? 'Calculando…' : 'No disponible'}</dd></div><div><dt>Tiempo de conducción{routing.missingStops > 0 ? ' (parcial)' : ''}</dt><dd>{routing.data ? formatRouteDuration(Math.ceil(routing.data.durationSeconds / 60)) : routing.loading ? 'Calculando…' : 'No disponible'}</dd></div></dl>
    {notice && <p className="route-success" role="status"><CheckCircle2 size={19} aria-hidden="true" />{notice}</p>}
    {mutation.isError && !editing && <RouteError error={mutation.error} />}
    <DeliveryRouteMap route={route} routing={routing} />
    {route.packagesWithoutLocation > 0 && <p className="route-warning" role="status"><CircleAlert size={20} aria-hidden="true" />{route.packagesWithoutLocation} paquete(s) sin ubicación en el mapa. Revisá su domicilio en la lista de paradas.</p>}
    {editing && !editable && <div className="route-warning" role="status"><CircleAlert size={20} aria-hidden="true" /><div><p>El recorrido cambió de estado y ya no permite guardar esta edición.</p><button className="route-button" type="button" disabled={busy} onClick={cancelEditing}>Salir de edición</button></div></div>}

    {editable && !editing && <>
      <div className="route-actions">
        <button className="route-button" type="button" disabled={busy} onClick={() => { mutation.reset(); setNotice(''); onEditingChange(true) }}><Pencil size={17} aria-hidden="true" /> Editar paradas</button>
        <button className="route-button" type="button" disabled={busy} onClick={() => execute({ id, action: 'optimize' })}><WandSparkles size={17} aria-hidden="true" /> Optimizar orden</button>
      </div>
      <form className="route-assignment" onSubmit={assign}>
        <div className="form-field"><label htmlFor="route-assignment">Reasignar repartidor</label><select className="form-control" id="route-assignment" value={driverId} onChange={(event) => setDriverId(event.target.value)} disabled={busy} required><option value="">Elegí otro repartidor</option>{candidates.filter((driver) => driver.id !== route.driver.id).map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}</select></div>
        <button className="route-button" type="submit" disabled={busy || !driverId}><UserRound size={17} aria-hidden="true" /> Reasignar</button>
      </form>
    </>}

    {locationStop && editable ? <RouteLocationEditor route={route} stop={locationStop} busy={busy} onSave={saveLocation} onCancel={cancelEditing} /> : editing && editable ? <RoutePackageEditor route={route} busy={busy} onSave={save} onCancel={cancelEditing} /> : <section className="route-stops" aria-labelledby="route-stops-title">
      <h3 id="route-stops-title"><MapPin size={19} aria-hidden="true" /> Paradas en orden de visita</h3>
      <ol className="route-stops__list">{route.stops.map((stop) => <li key={stop.order}>
        <div className="route-stop-heading"><span className="route-stop-number">{stop.order}</span><div><strong>{stop.destination}</strong><small>{stop.type === 'SUCURSAL' ? 'Sucursal de destino' : 'Domicilio'}{stop.latitude == null || stop.longitude == null ? ' · Sin ubicación en el mapa' : ''}</small></div></div>
        {editable && !editing && stop.type === 'DOMICILIO' && (stop.latitude == null || stop.longitude == null) && <button className="route-button route-stop-locate" type="button" aria-label={`Ubicar domicilio de la parada ${stop.order}`} disabled={busy} onClick={() => { mutation.reset(); setNotice(''); setLocationStop(stop); onEditingChange(true) }}><MapPin size={17} aria-hidden="true" /> Ubicar domicilio</button>}
        <ul className="route-stop-packages">{stop.packages.map((item) => <li key={item.id}><strong>{item.code}</strong><p>{item.description} · {item.weightKg} kg</p><small>Destinatario: {item.recipientName}</small><span className="route-stop-packages__links"><Link to={`/seguimiento?token=${encodeURIComponent(item.trackingToken)}`} target="_blank" rel="noopener noreferrer">Ver seguimiento</Link><TraceLink code={item.code} className="route-alerts__trace" label="Trazabilidad" /></span></li>)}</ul>
      </li>)}</ol>
    </section>}

    {editable && !editing ? <footer className="route-detail__footer"><button className="route-button route-button--primary" type="button" disabled={busy} onClick={() => setConfirmation('start')}><Play size={17} aria-hidden="true" /> Iniciar recorrido</button><button className="route-button route-button--danger" type="button" disabled={busy} onClick={() => setConfirmation('delete')}><Trash2 size={17} aria-hidden="true" /> Eliminar recorrido</button></footer>
      : !editing && <p className="route-hint"><Route size={17} aria-hidden="true" /> Este recorrido está {routeStatusLabels[route.status].toLowerCase()} y ya no permite modificaciones.</p>}
    <button className="route-button route-detail__refresh" type="button" disabled={busy || editing || query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={16} className={query.isFetching ? 'loading-icon' : undefined} aria-hidden="true" /> Actualizar detalle</button>
    {confirmation && <ConfirmRouteAction title={confirmation === 'start' ? '¿Iniciar este recorrido?' : '¿Eliminar este recorrido?'} description={confirmation === 'start' ? 'Los paquetes saldrán de la sucursal y el cambio se verá en el seguimiento. El recorrido ya no podrá editarse ni eliminarse.' : 'Los paquetes quedarán disponibles para otra planificación. Los que sigan sin recorrido aparecerán en las alertas.'} confirmLabel={confirmation === 'start' ? 'Confirmar salida' : 'Eliminar recorrido'} pending={busy} onCancel={() => setConfirmation(null)} onConfirm={() => execute({ id, action: confirmation })} />}
  </section>
}
