import { MapView } from '../../../shared/components/MapView'
import { isMapPoint } from '../../../shared/utils/geo'
import './ShipmentMap.css'

interface ShipmentMapProps {
  latitude: number | null
  longitude: number | null
  /** `picker`: se elige el punto con un clic o arrastrando el marcador. `location`: solo muestra el punto. */
  mode: 'picker' | 'location'
  accessibleName: string
  initialCenter?: { latitude: number; longitude: number }
  onLocationChange?: (latitude: number, longitude: number) => void
}

export function ShipmentMap({ latitude, longitude, mode, accessibleName, initialCenter, onLocationChange }: ShipmentMapProps) {
  const picker = mode === 'picker'
  const located = isMapPoint(latitude, longitude)
  return <MapView
    className={`shipment-map${picker ? ' shipment-map--picker' : ''}`}
    label={accessibleName}
    maxZoom={16}
    fallbackCenter={initialCenter ? { lat: initialCenter.latitude, lon: initialCenter.longitude } : undefined}
    markers={located ? [{
      id: 'punto', kind: 'punto', lat: latitude!, lon: longitude!, title: picker ? 'Arrastrá para ajustar la ubicación' : accessibleName,
      draggable: picker, onDragEnd: picker ? onLocationChange : undefined,
    }] : []}
    onMapClick={picker ? onLocationChange : undefined}
  />
}
