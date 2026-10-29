import type { DistanceType, RouteStatus } from './types/route.types'

export const distanceLabels: Record<DistanceType, string> = { CORTA: 'Corta distancia', LARGA: 'Larga distancia' }
export const routeStatusLabels: Record<RouteStatus, string> = {
  GENERADO: 'Sin salir', EN_EDICION: 'Sin salir', EN_CURSO: 'En reparto', FINALIZADO: 'Finalizado',
}
export const routeStatusTone: Record<RouteStatus, string> = {
  GENERADO: 'badge--muted', EN_EDICION: 'badge--muted', EN_CURSO: 'badge--info', FINALIZADO: 'badge--success',
}

export function isRouteEditable(status: RouteStatus) {
  return status === 'GENERADO' || status === 'EN_EDICION'
}

export function formatRouteDistance(value: number | null) {
  return value == null ? 'Sin estimación' : `${new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 }).format(value)} km`
}

export function formatRouteDuration(value: number | null) {
  if (value == null) return 'Sin estimación'
  return value < 60 ? `${value} min` : `${Math.floor(value / 60)} h ${value % 60} min`
}

function isoDay(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function localToday() {
  return isoDay(new Date())
}

/** Corre una fecha `YYYY-MM-DD` una cantidad de días. */
export function shiftDay(day: string, days: number) {
  const [year, month, date] = day.split('-').map(Number)
  return isoDay(new Date(year, month - 1, date + days))
}

/** Los 7 días (lunes a domingo) de la semana de esa fecha. */
export function weekOf(day: string) {
  const [year, month, date] = day.split('-').map(Number)
  const monday = (new Date(year, month - 1, date).getDay() + 6) % 7
  return Array.from({ length: 7 }, (_, index) => shiftDay(day, index - monday))
}

const longDay = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })
const shortWeekday = new Intl.DateTimeFormat('es-AR', { weekday: 'short' })

export function dayParts(day: string) {
  const [year, month, date] = day.split('-').map(Number)
  const value = new Date(year, month - 1, date)
  return { weekday: shortWeekday.format(value).replace('.', ''), number: date, long: longDay.format(value) }
}

/** Por defecto: en la ciudad el repartidor vuelve a la sucursal; entre sucursales, no. */
export function returnsByDefault(distanceType: DistanceType) {
  return distanceType === 'CORTA'
}
