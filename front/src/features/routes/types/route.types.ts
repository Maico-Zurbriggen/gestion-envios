import type { ApiBranch, Branch } from '../../shipments/types/shipment.types'

export type DistanceType = 'CORTA' | 'LARGA'
export type RouteStatus = 'GENERADO' | 'EN_EDICION' | 'EN_CURSO' | 'FINALIZADO'

export interface ApiDriver {
  usuario_id: string
  nombre: string
  dni: string
  email: string
  telefono: string
  estado_usuario: string
  perfil_configurado: boolean
  sucursal_base: ApiBranch | null
  tipo_reparto: DistanceType | null
  activo: boolean | null
  disponible_para_recorridos: boolean
}

export interface ApiRouteSummary {
  id: string
  fecha: string
  tipo_distancia: DistanceType
  estado: RouteStatus
  generado_automaticamente: boolean
  sucursal_origen_id: number
  sucursal_origen_nombre: string
  repartidor: { usuario_id: string; nombre: string; telefono: string }
  cantidad_paradas: number
  cantidad_paquetes: number
  distancia_estimada_km: number | null
  duracion_estimada_min: number | null
  paquetes_entregados?: number
  paquetes_no_entregados?: number
  created_at: string
  updated_at: string
}

export interface ApiPendingPackage {
  paquete_id: string
  numero_paquete: string
  descripcion: string
  peso_kg: number
  destinatario_nombre: string
  destino: string
  token_seguimiento: string
  tiene_ubicacion: boolean
  motivo: string | null
  visitas_previas: number
  en_devolucion: boolean
}

export interface ApiRouteDetail extends ApiRouteSummary {
  orientacion_calles_grados: number
  vuelve_a_sucursal: boolean
  sucursal_origen: ApiBranch
  paradas: Array<{
    orden: number
    tipo_parada: 'DOMICILIO' | 'SUCURSAL'
    destino: string
    latitud: number | null
    longitud: number | null
    paquetes: Array<{
      paquete_id: string
      numero_paquete: string
      orden: number
      descripcion: string
      peso_kg: number
      estado: string
      estado_en_recorrido: string
      token_seguimiento: string
      destinatario_nombre: string
      destinatario_telefono: string
      visitas_previas?: number
      en_devolucion?: boolean
    }>
  }>
  trazado: Array<{ latitud: number; longitud: number }>
  paquetes_sin_ubicacion: number
  max_visitas?: number
  control_carga?: { estado: 'EN_CURSO' | 'CERRADO'; verificados: number; esperados: number } | null
}

export interface ApiRouteAlert {
  id: string
  paquete_id: string
  numero_paquete: string
  token_seguimiento: string
  destino: string
  motivo: string
  descripcion_motivo: string
  sucursal_actual_id: number | null
  recorrido_id: string | null
  resuelta: boolean
  created_at: string
  resuelta_at: string | null
}

export interface ApiRouteEnvelope<T> {
  status: 'success'
  message?: string | null
  data: T
  alertas?: ApiRouteAlert[]
}

export interface ApiGeneration {
  resumen: {
    paquetes_pendientes: number
    paquetes_asignados: number
    paquetes_sin_recorrido: number
    repartidores_disponibles: number
    recorridos_generados: number
    recorridos_reemplazados: number
  }
  recorridos: ApiRouteDetail[]
  alertas: ApiRouteAlert[]
}

export interface RouteApiErrorResponse {
  code?: string
  message?: string
  errors?: Array<{ field?: string; message?: string }>
}

export interface Driver {
  id: string
  name: string
  dni: string
  email: string
  phone: string
  accountStatus: string
  configured: boolean
  branch: Branch | null
  distanceType: DistanceType | null
  active: boolean | null
  available: boolean
}

export interface DeliveryRouteSummary {
  id: string
  date: string
  distanceType: DistanceType
  status: RouteStatus
  automatic: boolean
  branchId: number
  branchName: string
  driver: { id: string; name: string; phone: string }
  stopCount: number
  packageCount: number
  distanceKm: number | null
  durationMinutes: number | null
  delivered: number
  failed: number
  createdAt: string
  updatedAt: string
}

export interface ApiWaitingSummary {
  sin_llegar: number
  sucursales: Array<{ sucursal_id: number; nombre: string; a_domicilio: number; entre_sucursales: number; sin_llegar: number }>
}

/** Dónde hay paquetes esperando recorrido y cuántos todavía no llegaron a una sucursal. */
export interface WaitingSummary {
  notArrived: number
  branches: Array<{ id: number; name: string; home: number; between: number; notArrived: number }>
}

/** Paquete listo en la sucursal que todavía no tiene recorrido. */
export interface PendingPackage {
  id: string
  code: string
  description: string
  weightKg: number
  recipientName: string
  destination: string
  trackingToken: string
  located: boolean
  /** Por qué no se puede planificar todavía (por ejemplo, sin ubicación). */
  issue: string | null
  previousVisits: number
  isReturn: boolean
}

export interface NewRouteInput {
  branchId: number
  date: string
  distanceType: DistanceType
  driverId: string
  packages: string[]
}

export interface RoutePackage {
  id: string
  code: string
  order: number
  description: string
  weightKg: number
  status: string
  routeStatus: string
  trackingToken: string
  recipientName: string
  recipientPhone: string
  /** Visitas a domicilio sin éxito antes de este recorrido. */
  previousVisits: number
  /** Viaja de vuelta a la sucursal de origen. */
  isReturn: boolean
}

export interface RouteStop {
  order: number
  type: 'DOMICILIO' | 'SUCURSAL'
  destination: string
  latitude: number | null
  longitude: number | null
  packages: RoutePackage[]
}

export interface DeliveryRoute extends DeliveryRouteSummary {
  streetOrientation: number
  returnsToBranch: boolean
  branch: Branch
  stops: RouteStop[]
  path: Array<{ latitude: number; longitude: number }>
  packagesWithoutLocation: number
  maxVisits: number
  /** Escaneo de lo que subió al vehículo en la sucursal de origen, si se hizo. */
  loadControl: { status: 'EN_CURSO' | 'CERRADO'; verified: number; expected: number } | null
}

export interface RouteAlert {
  id: string
  packageId: string
  packageNumber: string
  trackingToken: string
  destination: string
  reason: string
  description: string
  branchId: number | null
  routeId: string | null
  resolved: boolean
  createdAt: string
}

interface RouteFilters {
  branchId: number
  date: string
  distanceType: DistanceType
}

/** Recorridos de un rango de días (la semana que se está viendo). */
export interface RouteRange {
  branchId: number
  distanceType: DistanceType
  from: string
  to: string
}

export interface GenerateRoutesInput extends RouteFilters {
  driverIds: string[]
}

export interface GenerationResult {
  message: string
  summary: {
    pending: number
    assigned: number
    unassigned: number
    drivers: number
    generated: number
    replaced: number
  }
  routes: DeliveryRoute[]
  alerts: RouteAlert[]
}

export interface RouteUpdate {
  route: DeliveryRoute | null
  message: string
  alerts: RouteAlert[]
}

export type RouteCommand =
  | { id: string; action: 'save'; packages: string[] }
  | { id: string; action: 'locate'; packageCode: string; latitude: number; longitude: number }
  | { id: string; action: 'assign'; driverId: string }
  | { id: string; action: 'optimize' | 'start' | 'delete' }

export interface DriverProfileInput {
  driverId: string
  branchId: number
  distanceType: DistanceType
  active: boolean
}
