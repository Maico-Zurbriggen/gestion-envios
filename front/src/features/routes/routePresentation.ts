import type { DeliveryRoute, DistanceType, RouteStatus } from './types/route.types'

export const distanceLabels: Record<DistanceType, string> = { CORTA: 'Corta distancia', LARGA: 'Larga distancia' }
export const routeStatusLabels: Record<RouteStatus, string> = {
  GENERADO: 'Generado', EN_EDICION: 'En edición', EN_CURSO: 'En curso', FINALIZADO: 'Finalizado',
}

export function isRouteEditable(status: RouteStatus) {
  return status === 'GENERADO' || status === 'EN_EDICION'
}

export function orderedPackages(route: DeliveryRoute) {
  return route.stops.flatMap((stop) => stop.packages.map((item) => ({ ...item, destination: stop.destination }))).sort((a, b) => a.order - b.order)
}

export function formatRouteDistance(value: number | null) {
  return value == null ? 'Sin estimación' : `${new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 }).format(value)} km`
}

export function formatRouteDuration(value: number | null) {
  if (value == null) return 'Sin estimación'
  return value < 60 ? `${value} min` : `${Math.floor(value / 60)} h ${value % 60} min`
}

export function localToday() {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
}
