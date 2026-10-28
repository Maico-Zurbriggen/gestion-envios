import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import Map, { Layer, Marker, NavigationControl, Source, type MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useTheme } from '../hooks/useTheme'
import './MapView.css'

/**
 * Mapa de toda la app, como en Rumbo: MapLibre con OpenFreeMap (gratis, sin clave, uso comercial permitido).
 * Para no depender de terceros, servir un PMTiles propio y apuntar VITE_MAP_STYLE_URL a su estilo.
 */
const STYLE_LIGHT = import.meta.env.VITE_MAP_STYLE_URL || 'https://tiles.openfreemap.org/styles/liberty'
const STYLE_DARK = import.meta.env.VITE_MAP_STYLE_DARK_URL || 'https://tiles.openfreemap.org/styles/dark'

/** Margen al encuadrar: abajo más grande para que la atribución no tape marcadores. */
const FIT_PADDING = { top: 56, left: 48, right: 56, bottom: 72 }
const ARGENTINA = { lat: -38.4161, lon: -63.6167 }

export type MarkerKind = 'parada' | 'origen' | 'vehiculo' | 'punto'

export interface MapMarker {
  id: string
  lat: number
  lon: number
  kind: MarkerKind
  /** Texto corto dentro del marcador (número de parada). */
  label?: string
  /** Descripción al pasar el mouse y para lectores de pantalla. */
  title?: string
  /** Rumbo en grados (vehículo). */
  heading?: number | null
  /** Pendiente, apagado (sin novedades), entregado, sin entregar o destacado. */
  tone?: 'default' | 'muted' | 'success' | 'danger' | 'active'
  draggable?: boolean
  onDragEnd?: (lat: number, lon: number) => void
  onClick?: () => void
}

function Pin({ marker }: { marker: MapMarker }) {
  const tone = `map-pin--${marker.tone ?? 'default'}`
  if (marker.kind === 'vehiculo') {
    return <span className={`map-pin map-pin--vehicle ${tone}`} title={marker.title}>
      <span className="map-pin__pulse" aria-hidden="true" />
      <svg viewBox="0 0 24 24" aria-hidden="true" style={{ transform: marker.heading != null ? `rotate(${marker.heading}deg)` : undefined }}>
        {marker.heading != null
          ? <path d="M12 2 4 20l8-4 8 4z" />
          : <path d="M3 13V6a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v2h3l3 4v4h-2a2.5 2.5 0 0 1-5 0H9a2.5 2.5 0 0 1-5 0H3v-3Zm13-3v3h4l-2-3h-2ZM6.5 17.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm10 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" />}
      </svg>
      {marker.label && <span className="map-pin__caption">{marker.label}</span>}
    </span>
  }
  if (marker.kind === 'origen') {
    return <span className="map-pin map-pin--origin" title={marker.title}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 8v13h6v-7h8v7h6V8z" /></svg>
    </span>
  }
  // Parada o punto elegido: gota con número.
  return <span className={`map-pin map-pin--drop ${tone}${marker.draggable ? ' is-draggable' : ''}`} title={marker.title}>
    <span className="map-pin__drop">
      <span className="map-pin__label">
        {marker.label ?? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 3 10v11h6v-6h6v6h6V10z" /></svg>}
      </span>
    </span>
  </span>
}

interface MapViewProps {
  markers: MapMarker[]
  /** Recorrido [longitud, latitud]. */
  route?: Array<[number, number]> | null
  className?: string
  /** Nombre accesible del mapa. */
  label: string
  /** Centro si no hay marcadores. */
  fallbackCenter?: { lat: number; lon: number }
  /** Re-encuadra cuando cambia esta clave (por defecto, cuando cambian los marcadores). */
  fitKey?: string
  maxZoom?: number
  onMapClick?: (lat: number, lon: number) => void
  children?: ReactNode
}

export function MapView({ markers, route, className = '', label, fallbackCenter, fitKey, maxZoom = 15, onMapClick, children }: MapViewProps) {
  const ref = useRef<MapRef>(null)
  const box = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()
  const [routeColor, setRouteColor] = useState('#d9701f')
  useEffect(() => {
    // El recorrido toma el color principal de la marca.
    const value = box.current ? getComputedStyle(box.current).getPropertyValue('--color-primary').trim() : ''
    if (value) setRouteColor(value)
  }, [theme])

  const key = fitKey ?? markers.map((m) => `${m.id}:${m.lat.toFixed(5)},${m.lon.toFixed(5)}`).join('|')
  const bounds = useMemo(() => {
    const points: Array<[number, number]> = markers.map((m) => [m.lon, m.lat])
    if (route?.length) points.push(...route)
    if (!points.length) return null
    let [minX, minY, maxX, maxY] = [points[0][0], points[0][1], points[0][0], points[0][1]]
    for (const [x, y] of points) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x)
      minY = Math.min(minY, y); maxY = Math.max(maxY, y)
    }
    return [[minX, minY], [maxX, maxY]] as [[number, number], [number, number]]
    // Solo se recalcula al cambiar la clave: mover el vehículo no re-encuadra el mapa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, route])

  useEffect(() => {
    if (bounds) ref.current?.fitBounds(bounds, { padding: FIT_PADDING, maxZoom, duration: 600 })
  }, [bounds, maxZoom])

  const center = markers[0] ?? fallbackCenter ?? ARGENTINA
  const routeGeo = useMemo(() => route && route.length > 1
    ? { type: 'Feature' as const, properties: {}, geometry: { type: 'LineString' as const, coordinates: route } }
    : null, [route])

  return <div ref={box} className={`map-view ${className}`} role="region" aria-label={label}>
    <Map
      ref={ref}
      initialViewState={{ latitude: center.lat, longitude: center.lon, zoom: markers.length || fallbackCenter ? 13 : 4 }}
      mapStyle={theme === 'dark' ? STYLE_DARK : STYLE_LIGHT}
      style={{ width: '100%', height: '100%' }}
      attributionControl={{ compact: true }}
      cooperativeGestures={false}
      onClick={onMapClick ? (event) => onMapClick(event.lngLat.lat, event.lngLat.lng) : undefined}
      onLoad={() => { if (bounds) ref.current?.fitBounds(bounds, { padding: FIT_PADDING, maxZoom, duration: 0 }) }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      {routeGeo && <Source id="recorrido" type="geojson" data={routeGeo}>
        <Layer id="recorrido-borde" type="line" paint={{ 'line-color': '#ffffff', 'line-width': 7, 'line-opacity': 0.9 }} layout={{ 'line-join': 'round', 'line-cap': 'round' }} />
        <Layer id="recorrido-linea" type="line" layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': routeColor, 'line-width': 4 }} />
      </Source>}
      {markers.map((marker) => <Marker key={marker.id} latitude={marker.lat} longitude={marker.lon} anchor={marker.kind === 'parada' || marker.kind === 'punto' ? 'bottom' : 'center'}
        draggable={marker.draggable}
        onDragEnd={marker.onDragEnd ? (event) => marker.onDragEnd!(event.lngLat.lat, event.lngLat.lng) : undefined}
        onClick={marker.onClick ? (event) => { event.originalEvent.stopPropagation(); marker.onClick!() } : undefined}>
        <Pin marker={marker} />
      </Marker>)}
      {children}
    </Map>
  </div>
}
