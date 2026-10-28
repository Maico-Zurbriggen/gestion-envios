import { useState } from 'react'
import { CheckCircle2, LocateFixed, Navigation, Play, RefreshCw, Truck } from 'lucide-react'
import { useMyRoute, useMyRoutes } from '../hooks/useDelivery'
import { useDriverGps } from '../hooks/useDriverGps'
import { DeliveryAction } from '../components/DeliveryAction'
import { DeliveryRouteMap } from '../../routes/components/DeliveryRouteMap'
import { useRoadRoute } from '../../routes/hooks/useRoadRoute'
import { distanceLabels, localToday, routeStatusLabels } from '../../routes/routePresentation'
import { Modal } from '../../../shared/components/Modal'
import { ScanWithCameraButton } from '../../../shared/components/ScanWithCameraButton'
import { PACKAGE_CODE_PATTERN } from '../../../shared/services/scannedCode'
import { getStatusLabel } from '../../tracking/trackingStatus'
import { canRegisterDelivery, findScannedDelivery } from '../deliveryValidation'
import '../../../shared/styles/operations.css'
import '../../routes/pages/DeliveryRoutesPage.css'
import './DriverDeliveryPage.css'

function DriverRoute({ id, onBack }: { id: string; onBack: () => void }) {
  const { detail, position, start } = useMyRoute(id)
  const route = detail.data
  const routing = useRoadRoute(route)
  const gps = useDriverGps(id, !detail.isError && route?.status === 'EN_CURSO')
  const [packageCode, setPackageCode] = useState('')
  const [confirmStart, setConfirmStart] = useState(false)
  const pendingPackages = route?.stops.flatMap((stop) => stop.packages).filter((item) => item.routeStatus === 'PENDIENTE').length ?? 0

  // El código leído abre el mismo registro que "Registrar entrega o visita" de ese paquete.
  function openScannedPackage(code: string) {
    if (!route || detail.isError) return 'No pudimos verificar el recorrido. Actualizalo y volvé a intentar.'
    if (packageCode) return 'Terminá o cancelá el registro en curso antes de escanear otro paquete.'
    const match = findScannedDelivery(route, code)
    if (match.kind === 'not-in-route') return `El paquete ${code} no pertenece a este recorrido.`
    if (match.kind === 'not-enabled') {
      if (match.reason === 'already-visited') return `El paquete ${code} ya tiene su visita registrada en este recorrido.`
      if (match.reason === 'branch-stop') return `El paquete ${code} va a una sucursal: no se registra como entrega a domicilio.`
      if (match.reason === 'route-not-active') return 'Este recorrido no admite registrar entregas en este momento.'
      return `El paquete ${code} todavía no está habilitado para entrega (estado: ${getStatusLabel(match.item.status)}).`
    }
    setPackageCode(match.item.code)
  }
  return <div className="ops-stack">
    {!packageCode && <button className="ops-button" type="button" onClick={onBack} disabled={start.isPending}><Truck size={18} aria-hidden="true" /> Volver a mis recorridos</button>}
    {detail.isPending && <p role="status">Cargando recorrido…</p>}
    {detail.isError && <div className="form-error" role="alert">{detail.error.message}<button className="ops-button" type="button" disabled={detail.isFetching} onClick={() => void detail.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar</button></div>}
    {route && <>
      <section className="ops-panel ops-stack" aria-label="Resumen del recorrido">
        <h2>{distanceLabels[route.distanceType]} · {route.branchName}</h2><p>{route.date} · {routeStatusLabels[route.status]} · {pendingPackages} de {route.packageCount} paquetes pendientes</p>
        <button className="ops-button" type="button" disabled={detail.isFetching || start.isPending} onClick={() => { void detail.refetch(); void position.refetch() }}><RefreshCw size={18} aria-hidden="true" /> Actualizar recorrido</button>
        {route.status === 'GENERADO' && !detail.isError && <div className="ops-stack">
          <button className="ops-button ops-button--primary" type="button" aria-haspopup="dialog" onClick={() => setConfirmStart(true)}><Play size={18} aria-hidden="true" /> Iniciar recorrido</button>
          <Modal open={confirmStart} onClose={() => { if (!start.isPending) setConfirmStart(false) }} size="narrow" icon={Play} eyebrow="Mi reparto" title="¿Listo para salir?" description="¿Confirmás que estás listo para salir? Los paquetes pasarán a traslado o reparto."
            footer={<><button className="ops-button" type="button" disabled={start.isPending} onClick={() => setConfirmStart(false)}>Cancelar</button><button className="ops-button ops-button--primary" type="button" disabled={start.isPending} onClick={() => start.mutate(undefined, { onSuccess: () => setConfirmStart(false) })}><Play size={18} aria-hidden="true" />{start.isPending ? 'Iniciando…' : 'Confirmar inicio'}</button></>}>
            <p className="ops-hint">El seguimiento público mostrará el cambio de estado de cada paquete{route.distanceType === 'CORTA' ? ' y cada destinatario recibe el aviso de que su paquete llega hoy' : ''}.</p>
            {route.loadControl?.status === 'CERRADO'
              ? <p className="ops-success driver-load"><CheckCircle2 size={18} aria-hidden="true" /> Carga controlada en la sucursal: {route.loadControl.verified} de {route.loadControl.expected} paquetes escaneados.</p>
              : <p className="ops-warning driver-load">La carga de este recorrido {route.loadControl ? 'se está controlando' : 'no se controló'} en la sucursal. Antes de salir, revisá que lleves los {route.packageCount} paquetes.</p>}
          </Modal>
        </div>}
        {route.status === 'EN_EDICION' && <p role="status">El recorrido está en edición. Logística debe guardarlo antes de iniciar.</p>}
        {start.isError && <p className="form-error" role="alert">{start.error.message} Actualizá el recorrido para verificar su estado.</p>}
        {route.status === 'EN_CURSO' && !detail.isError && <div className="ops-stack">
          <p>Activá la ubicación y mantené esta pantalla abierta durante el reparto. El navegador puede suspender el GPS si bloqueás el teléfono o cambiás de aplicación.</p>
          <button className={`ops-button${gps.enabled ? '' : ' ops-button--primary'}`} type="button" onClick={gps.toggle}><LocateFixed size={18} aria-hidden="true" />{gps.enabled ? 'Dejar de compartir ubicación' : 'Activar ubicación GPS'}</button>
          <p role="status">{gps.sending ? 'Enviando ubicación…' : gps.enabled ? 'GPS activo. Se envía como máximo una posición cada 10 segundos.' : 'GPS desactivado.'}</p>
          {route.distanceType === 'LARGA' && <p className="ops-hint">La llegada a la siguiente sucursal se registra automáticamente al informar una posición dentro de 10 km. Se respeta el orden de paradas. Al descargar, el personal de la sucursal escanea cada paquete en Carga y descarga: entregá solo los que bajan ahí.</p>}
        </div>}
        {gps.error && <p className="form-error" role="alert">{gps.error}</p>}
        {position.data && <p className="ops-hint">Última ubicación recibida: {new Date(position.data.updatedAt).toLocaleString('es-AR')} · {position.data.latitude.toFixed(5)}, {position.data.longitude.toFixed(5)}</p>}
        {position.isError && <p role="alert">{position.error.message}</p>}
        {route.status === 'FINALIZADO' && <p className="ops-success" role="status"><CheckCircle2 size={20} aria-hidden="true" /> Recorrido finalizado. Ya no se comparte ubicación.</p>}
        <DeliveryRouteMap route={route} routing={routing} position={position.data} />
      </section>
      {packageCode && <DeliveryAction key={packageCode} routeId={id} code={packageCode} visitNumber={(route.stops.flatMap((stop) => stop.packages).find((item) => item.code === packageCode)?.previousVisits ?? 0) + 1} maxVisits={route.maxVisits} onClose={() => { setPackageCode(''); void detail.refetch() }} />}
      <section className="ops-panel ops-stack" aria-labelledby="driver-stops-title"><h2 id="driver-stops-title">Paradas en orden</h2>
        {route.distanceType === 'CORTA' && route.status === 'EN_CURSO' && !detail.isError && <div className="ops-actions">
          <ScanWithCameraButton mode="single" label="Escanear paquete" pattern={PACKAGE_CODE_PATTERN} patternMessage={(read) => `${read} no es un código de paquete (PAQ-XXXXXXXXXX).`} onScan={openScannedPackage} disabled={Boolean(packageCode)}
            description="Apuntá la cámara trasera a la etiqueta del paquete que vas a entregar. Se abre el registro de esa entrega." />
        </div>}
        <ol className="ops-list">{route.stops.map((stop) => <li key={stop.order} className="ops-panel ops-stop"><h3><span className="ops-stop__number">{stop.order}</span> {stop.destination}</h3>
          {stop.latitude != null && stop.longitude != null ? <a className="ops-button" href={`https://www.google.com/maps/dir/?api=1&destination=${stop.latitude},${stop.longitude}`} target="_blank" rel="noopener noreferrer"><Navigation size={18} aria-hidden="true" /> Navegar a esta parada</a> : <p className="ops-hint">Sin coordenadas. Consultá la dirección con logística antes de salir.</p>}
          <ul className="ops-list">{stop.packages.map((item) => <li key={item.id}><strong>{item.code}</strong>{item.isReturn && <span className="badge badge--info driver-badge">Devolución a origen</span>}{route.distanceType === 'CORTA' && <span className={`badge driver-badge ${item.previousVisits + 1 >= route.maxVisits ? 'badge--warning' : 'badge--muted'}`}>{item.previousVisits + 1}.ª de {route.maxVisits} visitas</span>}<p>{item.description} · {item.weightKg} kg</p><p>{item.recipientName} · {getStatusLabel(item.status)} · {stopStatusLabels[item.routeStatus] ?? item.routeStatus}</p>
            {canRegisterDelivery(route, stop, item) && !detail.isError && <button className="ops-button ops-button--primary" type="button" disabled={Boolean(packageCode)} onClick={() => setPackageCode(item.code)}><CheckCircle2 size={18} aria-hidden="true" /> Registrar entrega o visita</button>}
          </li>)}</ul>
        </li>)}</ol>
      </section>
    </>}
  </div>
}

const stopStatusLabels: Record<string, string> = {
  PENDIENTE: 'Pendiente de visita',
  ENTREGADO: 'Entregado',
  FALLIDO: 'Visita sin entrega',
}

export default function DriverDeliveryPage() {
  const [date, setDate] = useState(localToday())
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState('')
  const routes = useMyRoutes(date, status)
  return <div className="ops-page"><header className="ops-page__header"><span className="eyebrow"><Truck size={15} aria-hidden="true" /> Reparto</span><h1>Mi reparto</h1><p>Consultá tus recorridos, seguí las paradas y registrá el resultado de cada visita.</p></header>
    {selected ? <DriverRoute key={selected} id={selected} onBack={() => setSelected('')} /> : <>
      <section className="ops-panel ops-stack" aria-label="Filtros de mis recorridos"><div className="ops-grid">
        <label className="form-field" htmlFor="driver-date">Fecha (vacía para todas)<input className="form-control" id="driver-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        <label className="form-field" htmlFor="driver-status">Estado<select className="form-control" id="driver-status" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Todos</option>{Object.entries(routeStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      </div><button className="ops-button" type="button" disabled={routes.isFetching} onClick={() => void routes.refetch()}><RefreshCw size={18} aria-hidden="true" /> Actualizar recorridos</button></section>
      {routes.isFetching && <p role="status">Consultando tus recorridos…</p>}{routes.isError && <p className="form-error" role="alert">{routes.error.message}</p>}
      {routes.data?.length === 0 && <p role="status">No tenés recorridos asignados para estos filtros.</p>}
      <ul className="ops-list">{!routes.isError && routes.data?.map((route) => <li className="ops-panel ops-card" key={route.id}><h2>{distanceLabels[route.distanceType]} · {route.branchName}</h2><p>{route.date} · {routeStatusLabels[route.status]} · {route.stopCount} paradas · {route.packageCount} paquetes</p><button className="ops-button ops-button--primary" type="button" onClick={() => setSelected(route.id)}><Truck size={18} aria-hidden="true" /> Abrir recorrido</button></li>)}</ul>
    </>}
  </div>
}
