export interface RoadPoint {
  latitude: number
  longitude: number
}

export interface RoadRoute {
  /** Recorrido [longitud, latitud] para dibujar. */
  path: Array<[number, number]>
  distanceMeters: number
  durationSeconds: number
  /** Sin cálculo por calles: línea recta con distancia y tiempo aproximados. */
  approximate: boolean
}

export interface RoadRoutePlan {
  /** La ida: sucursal y paradas en orden. */
  points: RoadPoint[]
  /** La vuelta a la sucursal desde la última parada (vacío si el recorrido no vuelve). */
  returnPoints: RoadPoint[]
  missingStops: number
}

/** Ida y vuelta por calles; distancia y tiempo son los del total. */
export interface RoadTrip extends RoadRoute {
  returnPath: Array<[number, number]> | null
}

export interface RoadRoutingState {
  data: RoadTrip | undefined
  loading: boolean
  missingStops: number
  /** Puntos en orden, para dibujar algo mientras llega el recorrido por calles. */
  points: RoadPoint[]
}
