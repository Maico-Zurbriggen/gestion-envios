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
    tipo_entrega?: 'domicilio' | 'sucursal'
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
  deliveryType: 'domicilio' | 'sucursal'
  destination: string
  latitude: number | null
  longitude: number | null
  packages: TrackedPackage[]
}

export interface ApiPickupOptionBranch {
  id: number
  nombre: string
  provincia: string
  ciudad: string
  direccion: string
  latitud: number | null
  longitud: number | null
  es_sucursal_asignada: boolean
}

export interface PickupOptionsSuccessResponse {
  status: 'success'
  data: {
    token_seguimiento: string
    aplica_retiro: boolean
    motivo_no_aplica: string | null
    sucursal_asignada: ApiPickupOptionBranch | null
    paquetes: Array<{ numero_paquete: string; estado: string; disponible_para_retirar: boolean }>
    requisitos_retiro: { titular: string; tercero_autorizado: string }
  }
}

export interface PickupOptions {
  applies: boolean
  reason: string | null
  branch: { name: string; address: string; city: string; province: string; latitude: number | null; longitude: number | null } | null
  packages: Array<{ packageNumber: string; ready: boolean }>
  requirements: { recipient: string; authorizedPerson: string }
}
