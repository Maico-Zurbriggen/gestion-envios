import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './LocationMap.css'

export interface MapLocation { latitude: number; longitude: number; label: string }
export function LocationMap({ locations, name }: { locations: MapLocation[]; name: string }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layers = useRef<L.FeatureGroup | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (!container.current) return
    const map = L.map(container.current, { center: [-38.4, -63.6], zoom: 4, scrollWheelZoom: false })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).on('tileerror', () => setFailed(true)).addTo(map)
    mapRef.current = map
    layers.current = L.featureGroup().addTo(map)
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(container.current)
    return () => { observer.disconnect(); map.remove(); mapRef.current = null; layers.current = null }
  }, [])
  useEffect(() => {
    const map = mapRef.current
    const group = layers.current
    if (!map || !group) return
    group.clearLayers()
    locations.forEach((point, index) => {
      if (!Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) return
      const marker = document.createElement('span'); marker.textContent = String(index + 1)
      const popup = document.createElement('span'); popup.textContent = point.label
      L.marker([point.latitude, point.longitude], { title: point.label, icon: L.divIcon({ html: marker, className: 'location-map__marker', iconSize: [30, 30] }) }).bindPopup(popup).addTo(group)
    })
    const bounds = group.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds.pad(.2), { maxZoom: 15, animate: false })
  }, [locations])
  return <div className="location-map-panel"><div ref={container} className="location-map" role="region" aria-label={name} />{failed && <p role="status">No se pudo cargar parte del mapa. Las ubicaciones se detallan debajo.</p>}<ol>{locations.map((point, index) => <li key={`${index}-${point.label}`}>{point.label}: {point.latitude.toFixed(5)}, {point.longitude.toFixed(5)}</li>)}</ol></div>
}
