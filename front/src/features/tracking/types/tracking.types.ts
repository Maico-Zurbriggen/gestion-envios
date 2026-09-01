export interface ApiTrackedPackage {
  numero_paquete: string
  estado: string
  descripcion: string
  observaciones: string | null
  fecha_registro: string
  ultima_actualizacion: string
}

export interface TrackingSuccessResponse {
  status: 'success'
  data: {
    token_seguimiento: string
    destino: string
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
}

export interface ShipmentTracking {
  trackingToken: string
  destination: string
  packages: TrackedPackage[]
}
