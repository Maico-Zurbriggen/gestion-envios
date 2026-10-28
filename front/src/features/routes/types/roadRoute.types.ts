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
  points: RoadPoint[]
  missingStops: number
}

export interface RoadRoutingState {
  data: RoadRoute | undefined
  loading: boolean
  missingStops: number
  /** Puntos en orden, para dibujar algo mientras llega el recorrido por calles. */
  points: RoadPoint[]
}
