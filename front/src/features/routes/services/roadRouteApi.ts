import { operationalRequest } from '../../../shared/services/operationalApi'
import { isMapPoint } from '../../../shared/utils/geo'
import type { DeliveryRoute } from '../types/route.types'
import type { RoadPoint, RoadRoute, RoadRoutePlan } from '../types/roadRoute.types'

/** Puntos del recorrido en orden: la sucursal, las paradas ubicadas y, si corresponde, la vuelta. */
export function planRoadRoute(route: DeliveryRoute): RoadRoutePlan {
  const missingStops = route.stops.filter((stop) => !isMapPoint(stop.latitude, stop.longitude)).length
  const origin = isMapPoint(route.branch.latitude, route.branch.longitude)
    ? [{ latitude: route.branch.latitude!, longitude: route.branch.longitude! }]
    : []
  const stops = [...route.stops].sort((a, b) => a.order - b.order)
    .filter((stop) => isMapPoint(stop.latitude, stop.longitude))
    .map((stop) => ({ latitude: stop.latitude!, longitude: stop.longitude! }))
  const points: RoadPoint[] = [...origin, ...stops, ...(route.returnsToBranch ? origin : [])]
    .filter((point, index, all) => index === 0 || point.latitude !== all[index - 1].latitude || point.longitude !== all[index - 1].longitude)
  return { points, missingStops }
}

/** Recorrido por calles desde el backend (OSRM, como en Rumbo). Sin OSRM llega estimado, en línea recta. */
export async function getRoadRoute(points: RoadPoint[], token: string, signal?: AbortSignal): Promise<RoadRoute> {
  const { data } = await operationalRequest<{ data: { geometria: Array<[number, number]>; distancia_m: number; duracion_s: number; estimado: boolean } }>(
    '/mapa/trayecto', token,
    { method: 'POST', signal, body: JSON.stringify({ puntos: points.map((point) => ({ latitud: point.latitude, longitud: point.longitude })) }) },
  )
  return { path: data.geometria, distanceMeters: data.distancia_m, durationSeconds: data.duracion_s, approximate: data.estimado }
}
