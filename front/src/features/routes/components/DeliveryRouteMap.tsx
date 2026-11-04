import { LoaderCircle } from 'lucide-react'
import { MapView, type MapMarker } from '../../../shared/components/MapView'
import { isMapPoint } from '../../../shared/utils/geo'
import type { DeliveryRoute, RouteStop } from '../types/route.types'
import type { RoadRoutingState } from '../types/roadRoute.types'
import '../routes.css'

/** Color de cada parada: entregada, sin entregar, la próxima (en reparto) o pendiente. */
function stopTone(stop: RouteStop, isNext: boolean): MapMarker['tone'] {
  const states = stop.packages.map((item) => item.routeStatus)
  if (states.every((state) => state === 'ENTREGADO')) return 'success'
  if (!states.includes('PENDIENTE')) return 'danger'
  return isNext ? 'active' : 'default'
}

/** Mapa de un recorrido: sucursal, paradas numeradas, recorrido por calles y la posición del vehículo. */
export function DeliveryRouteMap({ route, routing, position, className = '' }: {
  route: DeliveryRoute
  routing: RoadRoutingState
  position?: { latitude: number; longitude: number; updatedAt?: string } | null
  className?: string
}) {
  const live = route.status === 'EN_CURSO'
  const nextStop = live ? route.stops.find((stop) => stop.packages.some((item) => item.routeStatus === 'PENDIENTE')) : undefined
  const markers: MapMarker[] = []
  if (isMapPoint(route.branch.latitude, route.branch.longitude)) {
    markers.push({ id: 'origen', kind: 'origen', lat: route.branch.latitude!, lon: route.branch.longitude!, title: `Sucursal de partida: ${route.branch.name}` })
  }
  for (const stop of route.stops) {
    if (!isMapPoint(stop.latitude, stop.longitude)) continue
    markers.push({
      id: `parada-${stop.order}`, kind: 'parada', lat: stop.latitude!, lon: stop.longitude!, label: String(stop.order),
      tone: stopTone(stop, stop === nextStop), title: `${stop.order}. ${stop.destination}`,
    })
  }
  if (position && isMapPoint(position.latitude, position.longitude)) {
    markers.push({ id: 'vehiculo', kind: 'vehiculo', lat: position.latitude, lon: position.longitude, tone: 'active', title: `${route.driver.name}: última posición` })
  }
  // Solo se dibuja el recorrido real por calles y rutas: nunca diagonales entre paradas.
  const path = routing.data && !routing.data.approximate && routing.data.path.length > 1 ? routing.data.path : null
  const returnPath = path && routing.data?.returnPath && routing.data.returnPath.length > 1 ? routing.data.returnPath : null
  const unavailable = !routing.loading && routing.points.length > 1 && !path

  return <div className="delivery-map-panel">
    <MapView className={`delivery-map ${className}`} label={`Mapa del recorrido de ${route.driver.name}`} markers={markers} route={path} returnRoute={returnPath}
      fitKey={`${route.id}|${markers.filter((m) => m.kind !== 'vehiculo').map((m) => m.id).join(',')}`} />
    <ul className="map-legend" aria-label="Referencias del mapa">
      <li><span className="map-legend__origin" aria-hidden="true" /> Sucursal</li>
      <li><span className="map-legend__dot" aria-hidden="true" /> {live ? 'Pendiente' : 'Parada'}</li>
      {live && <li><span className="map-legend__dot map-legend__dot--success" aria-hidden="true" /> Entregada</li>}
      {live && <li><span className="map-legend__dot map-legend__dot--danger" aria-hidden="true" /> Sin entregar</li>}
      {path && <li><span className="map-legend__line" aria-hidden="true" /> {returnPath ? 'Ida por calles' : 'Recorrido por calles'}</li>}
      {returnPath && <li><span className="map-legend__line map-legend__line--return" aria-hidden="true" /> Vuelta a la sucursal</li>}
    </ul>
    {routing.loading && <p className="route-hint delivery-map__loading" role="status"><LoaderCircle size={15} className="loading-icon" aria-hidden="true" /> Calculando el recorrido por calles…</p>}
    {unavailable && <p className="route-hint" role="status">No se pudo calcular el recorrido por calles en este momento: se muestran las paradas en orden.</p>}
    {routing.missingStops > 0 && <p className="route-hint" role="status">{routing.missingStops} {routing.missingStops === 1 ? 'parada no tiene' : 'paradas no tienen'} ubicación y no {routing.missingStops === 1 ? 'aparece' : 'aparecen'} en el mapa.</p>}
  </div>
}
