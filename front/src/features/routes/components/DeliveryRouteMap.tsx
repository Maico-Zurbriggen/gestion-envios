import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { LoaderCircle, RefreshCw } from 'lucide-react'
import 'leaflet/dist/leaflet.css'
import { isRoadPoint } from '../services/mapboxRoutingApi'
import type { DeliveryRoute } from '../types/route.types'
import type { RoadRoutingState } from '../types/roadRoute.types'
import '../routes.css'

export function DeliveryRouteMap({ route, routing, position }: { route: DeliveryRoute; routing: RoadRoutingState; position?: { latitude: number; longitude: number } | null }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layersRef = useRef<L.FeatureGroup | null>(null)
  const [tileError, setTileError] = useState(false)

  useEffect(() => {
    if (!container.current) return
    const element = container.current
    const map = L.map(element, { center: [-38.4161, -63.6167], zoom: 4, scrollWheelZoom: false })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).on('tileerror', () => setTileError(true)).addTo(map)
    map.attributionControl.addAttribution('Rutas &copy; <a href="https://www.mapbox.com/about/maps/" target="_blank" rel="noopener noreferrer">Mapbox</a>')
    mapRef.current = map
    layersRef.current = L.featureGroup().addTo(map)
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(element)
    return () => { resize.disconnect(); map.remove(); mapRef.current = null; layersRef.current = null }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !position) return
    const point = L.circleMarker([position.latitude, position.longitude], { radius: 9, className: 'delivery-map__driver' }).bindTooltip('Última posición del repartidor').addTo(map)
    return () => { point.remove() }
  }, [position])

  useEffect(() => {
    const map = mapRef.current
    const layers = layersRef.current
    if (!map || !layers) return
    layers.clearLayers()
    function addMarker(latitude: number, longitude: number, label: string, text: string, origin = false) {
      const marker = document.createElement('span')
      marker.textContent = label
      const popup = document.createElement('div')
      popup.textContent = text
      L.marker([latitude, longitude], { title: text,
        icon: L.divIcon({ html: marker, className: `delivery-map__marker${origin ? ' delivery-map__marker--origin' : ''}`, iconSize: [30, 30], iconAnchor: [15, 15] }),
      }).bindPopup(popup).addTo(layers!)
    }
    for (const segment of routing.data?.segments ?? []) {
      const points: L.LatLngTuple[] = segment.map((point) => [point.latitude, point.longitude])
      if (points.length > 1) L.polyline(points, { className: 'delivery-map__path', weight: 4 }).addTo(layers)
    }
    if (isRoadPoint(route.branch.latitude, route.branch.longitude)) addMarker(route.branch.latitude!, route.branch.longitude!, 'S', `Sucursal de partida: ${route.branch.name}`, true)
    for (const stop of route.stops) {
      if (isRoadPoint(stop.latitude, stop.longitude)) addMarker(stop.latitude!, stop.longitude!, String(stop.order), `Parada ${stop.order}: ${stop.destination}`)
    }
    const bounds = layers.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.18), { maxZoom: 15, animate: false })
  }, [route, routing.data])

  return <div className="delivery-map-panel">
    <div className="delivery-map" ref={container} role="region" aria-label={`Mapa del recorrido de ${route.driver.name}`} />
    {routing.loading && <p className="route-hint delivery-map__loading" role="status"><LoaderCircle size={17} className="loading-icon" aria-hidden="true" /> Calculando trayecto por calles…</p>}
    {routing.error && <div className="route-warning delivery-map__error" role="alert"><div><p>{routing.error.message}</p>{routing.canRetry && <button className="route-button" type="button" onClick={routing.retry} disabled={routing.fetching}><RefreshCw size={16} aria-hidden="true" /> Reintentar cálculo de calles</button>}</div></div>}
    <p className="route-hint">S: sucursal de partida. Los números indican el orden de las paradas. {route.returnsToBranch ? 'El recorrido vuelve a la sucursal.' : 'El recorrido termina en la última sucursal.'}</p>
    {routing.data && <p className="route-hint">Trayecto por calles calculado por <a href="https://www.mapbox.com/" target="_blank" rel="noopener noreferrer">Mapbox</a>, respetando el orden de las paradas. El tiempo es de conducción, sin atención en las paradas.</p>}
    {routing.data && routing.missingStops > 0 && <p className="route-warning" role="status">Trayecto parcial: {routing.missingStops} parada(s) sin coordenadas no se incluyen en la distancia ni en el tiempo por calles.</p>}
    {tileError && <p className="route-hint" role="status">No se pudo cargar parte del mapa base. Podés consultar las paradas en la lista.</p>}
  </div>
}
