import { OperationalApiError, operationalRequest } from '../../../shared/services/operationalApi'
import type {
  ApiAssignedRoute,
  ApiMonitorPackage,
  ApiMonitorPage,
  ApiMonitorSummary,
  ApiTrace,
  AssignedRoute,
  MonitorFilters,
  MonitorPackage,
  MonitorPage,
  MonitorSummary,
  PackageTrace,
} from '../types/monitor.types'

const BASE = '/admin/monitor'

function location(latitude: number | null, longitude: number | null) {
  return latitude !== null && longitude !== null ? { latitude, longitude } : null
}

function mapRoute(route: ApiAssignedRoute): AssignedRoute {
  return {
    id: route.id,
    date: route.fecha,
    status: route.estado,
    distanceType: route.tipo_distancia,
    driverName: route.repartidor_nombre,
    stop: route.orden,
    stopStatus: route.estado_en_recorrido,
  }
}

function mapPackage(item: ApiMonitorPackage): MonitorPackage {
  return {
    id: item.id,
    code: item.numero_paquete,
    status: item.estado,
    statusLabel: item.estado_etiqueta,
    group: item.grupo,
    description: item.descripcion,
    weightKg: item.peso_kg,
    shipmentId: item.envio_id,
    trackingToken: item.token_seguimiento,
    senderName: item.remitente_nombre,
    recipientName: item.destinatario_nombre,
    deliveryType: item.tipo_entrega,
    destination: item.destino,
    currentBranch: item.sucursal_actual,
    route: item.recorrido ? mapRoute(item.recorrido) : null,
    failedAttempts: item.intentos_fallidos,
    activeClaims: item.reclamos_en_curso,
    withoutRoute: item.sin_recorrido,
    isReturn: Boolean(item.en_devolucion),
    pickupUntil: item.retiro_hasta ?? null,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

/** Parámetros de consulta compartidos por el listado y la exportación. */
function filterParams(filters: MonitorFilters) {
  const params = new URLSearchParams()
  if (filters.search?.trim()) params.set('buscar', filters.search.trim())
  if (filters.group && filters.group !== 'TODOS') params.set('grupo', filters.group)
  if (filters.branchId) params.set('sucursal_id', String(filters.branchId))
  if (filters.deliveryType) params.set('tipo_entrega', filters.deliveryType)
  // Las fechas del filtro son días locales: se envían como medianoche de Argentina.
  if (filters.from) params.set('desde', `${filters.from}T00:00:00-03:00`)
  if (filters.to) {
    const next = new Date(`${filters.to}T00:00:00-03:00`)
    next.setUTCDate(next.getUTCDate() + 1)
    params.set('hasta', next.toISOString())
  }
  if (filters.order && filters.order !== 'movimiento') params.set('orden', filters.order)
  return params
}

export async function getMonitorSummary(token: string, branchId: number | null = null): Promise<MonitorSummary> {
  const query = branchId ? `?sucursal_id=${branchId}` : ''
  const { data } = await operationalRequest<{ data: ApiMonitorSummary }>(`${BASE}/resumen${query}`, token)
  return {
    totalPackages: data.total_paquetes,
    totalShipments: data.total_envios,
    byGroup: data.por_grupo,
    withoutRoute: data.sin_recorrido,
    withClaim: data.con_reclamo,
    withProblems: data.con_problemas,
    openClaims: data.reclamos_abiertos,
    failedNotifications: data.notificaciones_fallidas,
    today: {
      registered: data.hoy.registrados,
      received: data.hoy.ingresados,
      delivered: data.hoy.entregados,
      failedVisits: data.hoy.visitas_fallidas,
    },
    routesToday: {
      total: data.recorridos_hoy.total,
      generated: data.recorridos_hoy.generados,
      inProgress: data.recorridos_hoy.en_curso,
      finished: data.recorridos_hoy.finalizados,
      driversOnRoute: data.recorridos_hoy.repartidores_en_ruta,
    },
    branches: data.sucursales.map((branch) => ({ id: branch.id, name: branch.nombre })),
    generatedAt: data.generado_at,
  }
}

export async function listMonitorPackages(filters: MonitorFilters, token: string, signal?: AbortSignal): Promise<MonitorPage> {
  const params = filterParams(filters)
  if (filters.page && filters.page > 1) params.set('pagina', String(filters.page))
  if (filters.pageSize) params.set('por_pagina', String(filters.pageSize))
  const query = params.size ? `?${params}` : ''
  const { data } = await operationalRequest<{ data: ApiMonitorPage }>(`${BASE}/paquetes${query}`, token, { signal })
  return {
    packages: data.paquetes.map(mapPackage),
    total: data.total,
    page: data.pagina,
    pageSize: data.por_pagina,
    pages: data.paginas,
  }
}

export async function getPackageTrace(code: string, token: string): Promise<PackageTrace> {
  const { data } = await operationalRequest<{ data: ApiTrace }>(
    `${BASE}/paquetes/${encodeURIComponent(code.trim().toUpperCase())}`,
    token,
    undefined,
    { notFound: 'No encontramos un paquete con ese número. Revisá el código e intentá de nuevo.' },
  )
  return {
    package: mapPackage(data.paquete),
    notes: data.observaciones,
    scaleWeightKg: data.peso_admision_kg ?? null,
    originBranch: data.sucursal_origen ?? null,
    dimensions: { length: data.largo_cm, width: data.ancho_cm, height: data.alto_cm },
    sender: { name: data.remitente.nombre, document: data.remitente.documento, phone: data.remitente.telefono, email: data.remitente.email },
    recipient: {
      name: data.destinatario.nombre,
      document: data.destinatario.documento,
      phone: data.destinatario.telefono,
      email: data.destinatario.email,
    },
    destinationBranch: data.sucursal_destino,
    destinationAddress: data.direccion_destino,
    destinationLocation: location(data.latitud_destino, data.longitud_destino),
    siblings: data.paquetes_del_envio.map((item) => ({
      code: item.numero_paquete,
      status: item.estado,
      statusLabel: item.estado_etiqueta,
      group: item.grupo,
    })),
    routes: data.asignaciones.map((item) => ({ ...mapRoute(item), originBranch: item.sucursal_origen, assignedAt: item.asignado_at })),
    deliveries: data.entregas.map((item) => ({
      id: item.id,
      date: item.fecha,
      kind: item.tipo_evento,
      successful: item.resultado === 'EXITOSO',
      receiverName: item.receptor_nombre,
      receiverDocument: item.receptor_documento,
      authorized: item.es_autorizado,
      failureReason: item.motivo_fallo,
      hasSignature: item.con_firma,
      registeredBy: item.registrado_por,
      branch: item.sucursal,
      location: location(item.latitud, item.longitud),
    })),
    claims: data.reclamos.map((item) => ({
      id: item.id,
      type: item.tipo,
      status: item.estado,
      description: item.descripcion,
      resolution: item.resolucion,
      contactName: item.contacto_nombre,
      packageCode: item.numero_paquete,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
    notifications: data.notificaciones.map((item) => ({
      channel: item.canal,
      recipientType: item.destinatario_tipo,
      destination: item.destino,
      status: item.estado,
      reason: item.motivo,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
    timeline: data.linea_de_tiempo.map((event) => ({
      date: event.fecha,
      type: event.tipo,
      title: event.titulo,
      detail: event.detalle,
      actor: event.actor,
      place: event.lugar,
      tone: event.tono,
      latitude: event.latitud,
      longitude: event.longitud,
      deliveryEventId: event.evento_entrega_id,
      hasSignature: event.con_firma,
    })),
  }
}

/** Descarga un archivo binario autenticado (la imagen de una firma). */
async function downloadBlob(path: string, token: string, failure: string): Promise<Blob> {
  const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
  if (!apiUrl) throw new OperationalApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' })
  } catch {
    throw new OperationalApiError('No pudimos conectarnos. Revisá tu conexión y reintentá.')
  }
  if (response.status === 401) throw new OperationalApiError('Tu sesión venció. Iniciá sesión nuevamente.', 401)
  if (!response.ok) throw new OperationalApiError(failure, response.status)
  return response.blob()
}

export function getSignature(eventId: string, token: string) {
  return downloadBlob(`${BASE}/entregas/${eventId}/firma`, token, 'No pudimos cargar la firma de esta entrega.')
}
