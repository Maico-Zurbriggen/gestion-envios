export interface ApiTrackedPackage {
  numero_paquete: string
  estado: string
  descripcion: string
  observaciones: string | null
  fecha_registro: string
  ultima_actualizacion: string
  historial?: Array<{ estado_anterior: string | null; estado: string; fecha_hora: string; descripcion: string }>
  ubicacion_repartidor?: { latitud: number; longitud: number; actualizado_at: string } | null
}

export interface TrackingSuccessResponse {
  status: 'success'
  data: {
    token_seguimiento: string
    destino: string
    latitud_destino?: number | null
    longitud_destino?: number | null
    paquetes: ApiTrackedPackage[]
  }
}

export interface TrackedPackage {
  packageNumber: string
  status: string
  description: string
  notes: string | null
  registeredAt: string
  updatedAt: string
  history: Array<{ previousStatus: string | null; status: string; occurredAt: string; description: string }>
  driverLocation: { latitude: number; longitude: number; updatedAt: string } | null
}

export interface ShipmentTracking {
  trackingToken: string
  destination: string
  latitude: number | null
  longitude: number | null
  packages: TrackedPackage[]
}
