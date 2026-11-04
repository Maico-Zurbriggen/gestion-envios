import type { DeliveryRoute, RoutePackage, RouteStop } from '../routes/types/route.types'

export function receiverIsOldEnough(birthDate: string, today = new Date().toISOString().slice(0, 10)): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) return false
  const parsed = new Date(`${birthDate}T00:00:00Z`)
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== birthDate) return false
  const [year, month, day] = birthDate.split('-').map(Number)
  const [currentYear, currentMonth, currentDay] = today.split('-').map(Number)
  const age = currentYear - year - (currentMonth < month || (currentMonth === month && currentDay < day) ? 1 : 0)
  const anniversary = `${year + 16}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return birthDate <= today && anniversary < today && age <= 120
}

type RouteForDelivery = Pick<DeliveryRoute, 'distanceType' | 'status'>
type PackageForDelivery = Pick<RoutePackage, 'code' | 'routeStatus' | 'status'>

/** El repartidor puede registrar la entrega o visita de este paquete ahora. */
export function canRegisterDelivery(route: RouteForDelivery, stop: Pick<RouteStop, 'type'>, item: Pick<RoutePackage, 'routeStatus' | 'status'>): boolean {
  return route.distanceType === 'CORTA' && stop.type === 'DOMICILIO' && route.status === 'EN_CURSO' && item.routeStatus === 'PENDIENTE' && item.status === 'EN_REPARTO'
}

type ScannedDeliveryMatch<T extends PackageForDelivery> =
  | { kind: 'enabled'; item: T }
  | { kind: 'not-in-route' }
  | { kind: 'not-enabled'; item: T; reason: 'already-visited' | 'branch-stop' | 'not-in-delivery' | 'route-not-active' }

/** Busca un código leído entre las paradas del recorrido y dice si se puede registrar. */
export function findScannedDelivery<T extends PackageForDelivery>(
  route: RouteForDelivery & { stops: Array<Pick<RouteStop, 'type'> & { packages: T[] }> },
  code: string,
): ScannedDeliveryMatch<T> {
  const normalized = code.replace(/\s/g, '').toUpperCase()
  let fallback: ScannedDeliveryMatch<T> | null = null
  for (const stop of route.stops) {
    for (const item of stop.packages) {
      if (item.code.toUpperCase() !== normalized) continue
      if (canRegisterDelivery(route, stop, item)) return { kind: 'enabled', item }
      const reason = route.distanceType !== 'CORTA' || route.status !== 'EN_CURSO' ? 'route-not-active'
        : stop.type !== 'DOMICILIO' ? 'branch-stop'
          : item.routeStatus !== 'PENDIENTE' ? 'already-visited'
            : 'not-in-delivery'
      fallback ??= { kind: 'not-enabled', item, reason }
    }
  }
  return fallback ?? { kind: 'not-in-route' }
}
