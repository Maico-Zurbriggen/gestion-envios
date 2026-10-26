import type { DeliveryRoute } from '../types/route.types'
import type { MapboxDirectionsResponse, RoadPoint, RoadRoute, RoadRoutePlan } from '../types/roadRoute.types'

const directionsUrl = 'https://api.mapbox.com/directions/v5/mapbox/driving'
const accessToken = (import.meta.env.VITE_MAPBOX_ACCESS_TOKEN ?? import.meta.env.VITE_GESTION_ENVIOS_MAPBOX_TOKEN ?? '').trim()
const maxCoordinates = 25

export class MapboxRoutingError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'MapboxRoutingError'
  }
}

export function isRoadPoint(latitude: number | null, longitude: number | null): boolean {
  return latitude != null && longitude != null && Number.isFinite(latitude) && Number.isFinite(longitude)
    && latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
}

export function planRoadRoute(route: DeliveryRoute): RoadRoutePlan {
  const missingStops = route.stops.filter((stop) => !isRoadPoint(stop.latitude, stop.longitude)).length
  if (!isRoadPoint(route.branch.latitude, route.branch.longitude)) {
    return { points: [], missingStops, error: new MapboxRoutingError('La sucursal de partida no tiene una ubicación válida para calcular las calles.') }
  }
  const origin: RoadPoint = { latitude: route.branch.latitude!, longitude: route.branch.longitude! }
  const locatedStops = [...route.stops].sort((a, b) => a.order - b.order)
    .filter((stop) => isRoadPoint(stop.latitude, stop.longitude))
    .map((stop) => ({ latitude: stop.latitude!, longitude: stop.longitude! }))
  if (!locatedStops.length) {
    return { points: [origin], missingStops, error: new MapboxRoutingError('Las paradas no tienen ubicación en el mapa. Completá sus coordenadas para calcular el trayecto por calles.') }
  }
  const points = [origin, ...locatedStops, ...(route.returnsToBranch ? [origin] : [])]
    .filter((point, index, all) => index === 0 || point.latitude !== all[index - 1].latitude || point.longitude !== all[index - 1].longitude)
  return { points, missingStops, error: null }
}

async function requestDirections(points: RoadPoint[], signal?: AbortSignal): Promise<RoadRoute> {
  signal?.throwIfAborted()
  const coordinates = points.map((point) => `${point.longitude},${point.latitude}`).join(';')
  const params = new URLSearchParams({
    access_token: accessToken, geometries: 'geojson', overview: 'full', steps: 'false',
    alternatives: 'false', continue_straight: 'false', radiuses: points.map(() => '1000').join(';'),
  })
  const timeout = AbortSignal.timeout(15000)
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout
  let response: Response
  try {
    response = await fetch(`${directionsUrl}/${coordinates}?${params}`, {
      signal: requestSignal, headers: { Accept: 'application/json' },
    })
  } catch (error) {
    if (signal?.aborted) throw error
    if (timeout.aborted) throw new MapboxRoutingError('El cálculo de calles está demorando demasiado. Intentá nuevamente.')
    throw new MapboxRoutingError('No pudimos conectarnos con Mapbox. Revisá tu conexión y reintentá el cálculo de calles.')
  }
  const payload: unknown = await response.json().catch(() => null)
  signal?.throwIfAborted()
  if (timeout.aborted) throw new MapboxRoutingError('El cálculo de calles está demorando demasiado. Intentá nuevamente.')
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) throw new MapboxRoutingError('Mapbox no autorizó el cálculo de calles. Pedile al administrador que revise la configuración del servicio.')
    if (response.status === 429) throw new MapboxRoutingError('Mapbox está recibiendo demasiadas consultas. Esperá un momento antes de reintentar.')
    throw new MapboxRoutingError('No pudimos calcular el trayecto por calles en este momento. Intentá nuevamente.')
  }
  const result = payload as MapboxDirectionsResponse | null
  if (result?.code === 'NoRoute' || result?.code === 'NoSegment') {
    throw new MapboxRoutingError('Mapbox no encontró un camino transitable para estas ubicaciones. Revisá las coordenadas de las paradas.')
  }
  const route = result?.routes?.[0]
  if (result?.code !== 'Ok' || !route || !Number.isFinite(route.distance) || route.distance < 0
    || !Number.isFinite(route.duration) || route.duration < 0 || route.geometry?.type !== 'LineString'
    || !Array.isArray(route.geometry.coordinates) || route.geometry.coordinates.length < 2
    || !route.geometry.coordinates.every((point) => Array.isArray(point) && point.length >= 2 && isRoadPoint(point[1], point[0]))) {
    throw new MapboxRoutingError('No pudimos interpretar el trayecto de Mapbox. Intentá nuevamente.')
  }
  return { segments: [route.geometry.coordinates.map(([longitude, latitude]) => ({ latitude, longitude }))],
    distanceMeters: route.distance, durationSeconds: route.duration }
}

export async function getMapboxRoadRoute(points: RoadPoint[], signal?: AbortSignal): Promise<RoadRoute> {
  signal?.throwIfAborted()
  if (!accessToken) throw new MapboxRoutingError('El cálculo de calles todavía no está habilitado. Pedile al administrador que configure Mapbox.')
  if (!points.length || points.some((point) => !isRoadPoint(point.latitude, point.longitude))) {
    throw new MapboxRoutingError('El recorrido contiene ubicaciones inválidas. Revisá las coordenadas de las paradas.')
  }
  const result: RoadRoute = { segments: [], distanceMeters: 0, durationSeconds: 0 }
  // Consecutive requests share their boundary waypoint; their geometries stay separate.
  for (let start = 0; start < points.length - 1; start += maxCoordinates - 1) {
    const section = await requestDirections(points.slice(start, start + maxCoordinates), signal)
    result.segments.push(...section.segments)
    result.distanceMeters += section.distanceMeters
    result.durationSeconds += section.durationSeconds
  }
  return result
}
