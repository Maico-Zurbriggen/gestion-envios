export interface RoadPoint {
  latitude: number
  longitude: number
}

export interface RoadRoute {
  segments: RoadPoint[][]
  distanceMeters: number
  durationSeconds: number
}

export interface RoadRoutePlan {
  points: RoadPoint[]
  missingStops: number
  error: Error | null
}

export interface MapboxDirectionsResponse {
  code?: string
  routes?: Array<{
    distance: number
    duration: number
    geometry: { type: string; coordinates: number[][] }
  }>
}

export interface RoadRoutingState {
  data: RoadRoute | undefined
  error: Error | null
  loading: boolean
  fetching: boolean
  missingStops: number
  canRetry: boolean
  retry: () => void
}
