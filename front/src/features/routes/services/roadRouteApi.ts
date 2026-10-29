import { operationalRequest } from '../../../shared/services/operationalApi'
import { isMapPoint } from '../../../shared/utils/geo'
import type { DeliveryRoute } from '../types/route.types'
import type { RoadPoint, RoadRoute, RoadRoutePlan, RoadTrip } from '../types/roadRoute.types'

function withoutRepeats(points: RoadPoint[]) {
  return points.filter((point, index, all) => index === 0 || point.latitude !== all[index - 1].latitude || point.longitude !== all[index - 1].longitude)
}

/**
 * Puntos del recorrido en orden: la ida (sucursal y paradas ubicadas) y, si el recorrido
 * vuelve, el tramo aparte desde la última parada hasta la sucursal, para dibujarlo distinto.
 */
export function planRoadRoute(route: DeliveryRoute): RoadRoutePlan {
  const missingStops = route.stops.filter((stop) => !isMapPoint(stop.latitude, stop.longitude)).length
  const origin = isMapPoint(route.branch.latitude, route.branch.longitude)
    ? [{ latitude: route.branch.latitude!, longitude: route.branch.longitude! }]
    : []
  const stops = [...route.stops].sort((a, b) => a.order - b.order)
    .filter((stop) => isMapPoint(stop.latitude, stop.longitude))
    .map((stop) => ({ latitude: stop.latitude!, longitude: stop.longitude! }))
  const points = withoutRepeats([...origin, ...stops])
  const returnPoints = route.returnsToBranch && origin.length && stops.length
    ? withoutRepeats([stops[stops.length - 1], origin[0]])
    : []
  return { points, returnPoints: returnPoints.length > 1 ? returnPoints : [], missingStops }
}

/** Recorrido por calles desde el backend (OSRM, como en Rumbo). Sin OSRM llega estimado, en línea recta. */
export async function getRoadRoute(points: RoadPoint[], token: string, signal?: AbortSignal): Promise<RoadRoute> {
  const { data } = await operationalRequest<{ data: { geometria: Array<[number, number]>; distancia_m: number; duracion_s: number; estimado: boolean } }>(
    '/mapa/trayecto', token,
    { method: 'POST', signal, body: JSON.stringify({ puntos: points.map((point) => ({ latitud: point.latitude, longitud: point.longitude })) }) },
  )
  return { path: data.geometria, distanceMeters: data.distancia_m, durationSeconds: data.duracion_s, approximate: data.estimado }
}

/** La ida y, si hay, la vuelta: se piden juntas y se suman para la distancia y el tiempo totales. */
export async function getRoadTrip(plan: RoadRoutePlan, token: string, signal?: AbortSignal): Promise<RoadTrip> {
  const [outbound, back] = await Promise.all([
    getRoadRoute(plan.points, token, signal),
    plan.returnPoints.length > 1 ? getRoadRoute(plan.returnPoints, token, signal) : Promise.resolve(null),
  ])
  return {
    path: outbound.path,
    returnPath: back?.path ?? null,
    distanceMeters: outbound.distanceMeters + (back?.distanceMeters ?? 0),
    durationSeconds: outbound.durationSeconds + (back?.durationSeconds ?? 0),
    approximate: outbound.approximate || Boolean(back?.approximate),
  }
}
