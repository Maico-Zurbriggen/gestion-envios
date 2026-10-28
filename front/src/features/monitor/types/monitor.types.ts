export type PackageGroup = 'PENDIENTES' | 'EN_DEPOSITO' | 'EN_CAMINO' | 'PARA_RETIRAR' | 'NO_ENTREGADOS' | 'ENTREGADOS' | 'OTROS'
export type SpecialFilter = 'CON_PROBLEMAS' | 'SIN_RECORRIDO' | 'CON_RECLAMO'
export type GroupFilter = 'TODOS' | Exclude<PackageGroup, 'OTROS'> | SpecialFilter
export type MonitorOrder = 'movimiento' | 'recientes' | 'antiguos'

// --- Contratos de la API (snake_case) ---

export interface ApiMonitorSummary {
  total_paquetes: number
  total_envios: number
  por_grupo: Record<string, number>
  por_estado: Record<string, number>
  sin_recorrido: number
  con_reclamo: number
  con_problemas: number
  reclamos_abiertos: number
  notificaciones_fallidas: number
  hoy: { registrados: number; ingresados: number; entregados: number; visitas_fallidas: number }
  recorridos_hoy: { total: number; generados: number; en_curso: number; finalizados: number; repartidores_en_ruta: number }
  sucursales: Array<{ id: number; nombre: string }>
  generado_at: string
}

export interface ApiAssignedRoute {
  id: string
  fecha: string
  estado: string
  tipo_distancia: string
  repartidor_nombre: string
  orden: number
  estado_en_recorrido: string
}

export interface ApiMonitorPackage {
  id: string
  numero_paquete: string
  estado: string
  estado_etiqueta: string
  grupo: PackageGroup
  descripcion: string
  peso_kg: number
  envio_id: string
  token_seguimiento: string
  remitente_nombre: string
  destinatario_nombre: string
  tipo_entrega: 'domicilio' | 'sucursal'
  destino: string
  sucursal_actual: string | null
  recorrido: ApiAssignedRoute | null
  intentos_fallidos: number
  reclamos_en_curso: number
  sin_recorrido: boolean
  created_at: string
  updated_at: string
}

export interface ApiMonitorPage {
  paquetes: ApiMonitorPackage[]
  total: number
  pagina: number
  por_pagina: number
  paginas: number
}

export interface ApiTraceEvent {
  fecha: string
  tipo: TraceEventType
  titulo: string
  detalle: string | null
  actor: string | null
  lugar: string | null
  tono: Tone
  latitud: number | null
  longitud: number | null
  evento_entrega_id: string | null
  con_firma: boolean
}

export interface ApiTrace {
  paquete: ApiMonitorPackage
  observaciones: string | null
  largo_cm: number
  ancho_cm: number
  alto_cm: number
  remitente: { nombre: string; documento: string | null; telefono: string | null; email: string | null }
  destinatario: { nombre: string; documento: string | null; telefono: string | null; email: string | null }
  sucursal_destino: string | null
  direccion_destino: string | null
  latitud_destino: number | null
  longitud_destino: number | null
  paquetes_del_envio: Array<{ numero_paquete: string; estado: string; estado_etiqueta: string; grupo: PackageGroup }>
  asignaciones: Array<ApiAssignedRoute & { sucursal_origen: string; asignado_at: string }>
  entregas: Array<{
    id: string
    fecha: string
    tipo_evento: string
    resultado: string
    receptor_nombre: string | null
    receptor_documento: string | null
    es_autorizado: boolean
    motivo_fallo: string | null
    con_firma: boolean
    registrado_por: string | null
    sucursal: string | null
    latitud: number | null
    longitud: number | null
  }>
  reclamos: Array<{
    id: string
    tipo: string
    estado: string
    descripcion: string
    resolucion: string | null
    contacto_nombre: string
    numero_paquete: string | null
    created_at: string
    updated_at: string
  }>
  notificaciones: Array<{
    canal: string
    destinatario_tipo: string
    destino: string
    estado: string
    motivo: string
    created_at: string
    updated_at: string
  }>
  linea_de_tiempo: ApiTraceEvent[]
}

// --- Modelos de la aplicación (camelCase) ---

export type Tone = 'neutral' | 'info' | 'brand' | 'success' | 'warning' | 'danger'
export type TraceEventType = 'registro' | 'estado' | 'recorrido' | 'entrega' | 'alerta' | 'reclamo' | 'notificacion'

export interface MonitorSummary {
  totalPackages: number
  totalShipments: number
  byGroup: Record<string, number>
  withoutRoute: number
  withClaim: number
  withProblems: number
  openClaims: number
  failedNotifications: number
  today: { registered: number; received: number; delivered: number; failedVisits: number }
  routesToday: { total: number; generated: number; inProgress: number; finished: number; driversOnRoute: number }
  branches: Array<{ id: number; name: string }>
  generatedAt: string
}

export interface AssignedRoute {
  id: string
  date: string
  status: string
  distanceType: string
  driverName: string
  stop: number
  stopStatus: string
}

export interface MonitorPackage {
  id: string
  code: string
  status: string
  statusLabel: string
  group: PackageGroup
  description: string
  weightKg: number
  shipmentId: string
  trackingToken: string
  senderName: string
  recipientName: string
  deliveryType: 'domicilio' | 'sucursal'
  destination: string
  currentBranch: string | null
  route: AssignedRoute | null
  failedAttempts: number
  activeClaims: number
  withoutRoute: boolean
  createdAt: string
  updatedAt: string
}

export interface MonitorPage {
  packages: MonitorPackage[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface MonitorFilters {
  search?: string
  group?: GroupFilter
  branchId?: number | null
  deliveryType?: 'domicilio' | 'sucursal' | null
  from?: string | null
  to?: string | null
  order?: MonitorOrder
  page?: number
  pageSize?: number
}

export interface TraceEvent {
  date: string
  type: TraceEventType
  title: string
  detail: string | null
  actor: string | null
  place: string | null
  tone: Tone
  latitude: number | null
  longitude: number | null
  deliveryEventId: string | null
  hasSignature: boolean
}

export interface Person {
  name: string
  document: string | null
  phone: string | null
  email: string | null
}

export interface PackageTrace {
  package: MonitorPackage
  notes: string | null
  dimensions: { length: number; width: number; height: number }
  sender: Person
  recipient: Person
  destinationBranch: string | null
  destinationAddress: string | null
  destinationLocation: { latitude: number; longitude: number } | null
  siblings: Array<{ code: string; status: string; statusLabel: string; group: PackageGroup }>
  routes: Array<AssignedRoute & { originBranch: string; assignedAt: string }>
  deliveries: Array<{
    id: string
    date: string
    kind: 'ENTREGA_DOMICILIO' | 'RETIRO_SUCURSAL' | string
    successful: boolean
    receiverName: string | null
    receiverDocument: string | null
    authorized: boolean
    failureReason: string | null
    hasSignature: boolean
    registeredBy: string | null
    branch: string | null
    location: { latitude: number; longitude: number } | null
  }>
  claims: Array<{
    id: string
    type: string
    status: string
    description: string
    resolution: string | null
    contactName: string
    packageCode: string | null
    createdAt: string
    updatedAt: string
  }>
  notifications: Array<{
    channel: string
    recipientType: string
    destination: string
    status: string
    reason: string
    createdAt: string
    updatedAt: string
  }>
  timeline: TraceEvent[]
}
