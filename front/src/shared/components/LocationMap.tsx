import { isMapPoint } from '../utils/geo'
import { MapView, type MapMarker } from './MapView'
import './LocationMap.css'

export interface MapLocation {
  latitude: number
  longitude: number
  label: string
  /** `vehiculo`: posición del repartidor. Por defecto, un punto numerado. */
  kind?: 'punto' | 'vehiculo'
  tone?: MapMarker['tone']
}

/** Mapa con uno o más puntos (destino, entregas, posición del reparto) y sus referencias debajo. */
export function LocationMap({ locations, name }: { locations: MapLocation[]; name: string }) {
  const valid = locations.filter((point) => isMapPoint(point.latitude, point.longitude))
  // Los puntos se numeran en orden; la posición del vehículo no lleva número.
  const numbers = valid.map((point, index) => (point.kind === 'vehiculo' ? '' : String(valid.slice(0, index + 1).filter((item) => item.kind !== 'vehiculo').length)))
  const markers: MapMarker[] = valid.map((point, index) => point.kind === 'vehiculo'
    ? { id: `ubicacion-${index}`, kind: 'vehiculo', lat: point.latitude, lon: point.longitude, title: point.label, tone: 'active' }
    : { id: `ubicacion-${index}`, kind: 'parada', lat: point.latitude, lon: point.longitude, label: numbers[index], title: point.label, tone: point.tone })
  return <div className="location-map-panel">
    <MapView className="location-map" label={name} markers={markers} />
    <ol className="location-map__legend">
      {valid.map((point, index) => <li key={`${index}-${point.label}`}>
        <span className={`location-map__key${point.kind === 'vehiculo' ? ' is-vehicle' : ''}`} aria-hidden="true">{numbers[index]}</span>
        {point.label}
      </li>)}
    </ol>
  </div>
}
