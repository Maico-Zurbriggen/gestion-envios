import { useEffect, useRef } from 'react'
import L, { type CircleMarker, type Map as LeafletMap } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './ShipmentMap.css'

interface ShipmentMapProps {
  latitude: number | null
  longitude: number | null
  mode: 'picker' | 'location'
  accessibleName: string
  initialCenter?: { latitude: number; longitude: number }
  onLocationChange?: (latitude: number, longitude: number) => void
}

const ARGENTINA_CENTER: [number, number] = [-38.4161, -63.6167]

export function ShipmentMap({
  latitude,
  longitude,
  mode,
  accessibleName,
  initialCenter,
  onLocationChange,
}: ShipmentMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<LeafletMap | null>(null)
  const markerRef = useRef<CircleMarker | null>(null)
  const onLocationChangeRef = useRef(onLocationChange)
  const initialLatitude = initialCenter?.latitude ?? ARGENTINA_CENTER[0]
  const initialLongitude = initialCenter?.longitude ?? ARGENTINA_CENTER[1]
  const initialZoom = initialCenter ? 14 : 4

  useEffect(() => {
    onLocationChangeRef.current = onLocationChange
  }, [onLocationChange])

  useEffect(() => {
    if (!containerRef.current) return

    const map = L.map(containerRef.current, {
      center: [initialLatitude, initialLongitude],
      zoom: initialZoom,
      scrollWheelZoom: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)

    if (mode === 'picker') {
      map.on('click', (event) => {
        onLocationChangeRef.current?.(event.latlng.lat, event.latlng.lng)
      })
    }

    mapRef.current = map
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(containerRef.current)

    return () => {
      resize.disconnect()
      map.remove()
      mapRef.current = null
      markerRef.current = null
    }
  }, [mode, initialLatitude, initialLongitude, initialZoom])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const hasLocation =
      latitude !== null &&
      longitude !== null &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)

    if (!hasLocation) {
      markerRef.current?.remove()
      markerRef.current = null
      if (mode === 'location') map.setView(ARGENTINA_CENTER, 4)
      return
    }

    const position: [number, number] = [latitude, longitude]

    if (markerRef.current) {
      markerRef.current.setLatLng(position)
    } else {
      markerRef.current = L.circleMarker(position, {
        className: 'shipment-map__point',
        radius: 9,
        weight: 3,
        fillOpacity: 1,
      }).addTo(map)
    }

    if (mode === 'location') {
      map.setView(position, 15)
    } else {
      map.setView(position, Math.max(map.getZoom(), 14))
    }
  }, [latitude, longitude, mode])

  return (
    <div
      className={`shipment-map ${mode === 'picker' ? 'shipment-map--picker' : ''}`}
      ref={containerRef}
      role="application"
      aria-label={accessibleName}
    />
  )
}
