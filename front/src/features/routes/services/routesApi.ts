import type { ApiBranch, Branch } from '../../shipments/types/shipment.types'
import type {
  ApiDriver, ApiGeneration, ApiRouteAlert, ApiRouteDetail, ApiRouteEnvelope, ApiRouteSummary,
  DeliveryRoute, DeliveryRouteSummary, Driver, DriverProfileInput, GenerateRoutesInput,
  GenerationResult, RouteAlert, RouteApiErrorResponse, RouteCommand, RouteFilters, RouteUpdate,
} from '../types/route.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

export class RoutesApiError extends Error {
  readonly status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'RoutesApiError'
    this.status = status
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<ApiRouteEnvelope<T>> {
  if (!apiUrl) throw new RoutesApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...init?.headers },
    })
  } catch (error) {
    if (init?.signal?.aborted) throw error
    throw new RoutesApiError('No pudimos conectarnos. Revisá tu conexión e intentá nuevamente.')
  }
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    let message = 'No pudimos completar la operación. Intentá nuevamente.'
    if (response.status === 401) message = 'Tu sesión venció. Iniciá sesión nuevamente.'
    else if (response.status === 403) message = 'Tu cuenta no tiene permiso para gestionar recorridos.'
    else if (response.status === 404) message = 'No encontramos el recorrido, repartidor o paquete solicitado. Actualizá los datos.'
    else if (response.status >= 500) message = 'El servicio no está disponible. Intentá nuevamente más tarde.'
    else if ([400, 409, 422].includes(response.status)) {
      const error = payload as RouteApiErrorResponse | null
      const issues = Array.isArray(error?.errors) ? error.errors.map((issue) => issue?.message).filter(Boolean) : []
      message = issues.length ? [...new Set(issues)].join(' ') : error?.message || 'Revisá los datos y las condiciones del recorrido.'
    }
    throw new RoutesApiError(message, response.status)
  }
  const result = payload as ApiRouteEnvelope<T>
  if (result?.status !== 'success') throw new RoutesApiError('El servidor devolvió una respuesta inesperada. Actualizá los datos.')
  return result
}

function mapBranch(branch: ApiBranch): Branch {
  return { id: branch.id, name: branch.nombre, province: branch.provincia, city: branch.ciudad,
    address: branch.direccion, latitude: branch.latitud, longitude: branch.longitud }
}

function mapDriver(driver: ApiDriver): Driver {
  return { id: driver.usuario_id, name: driver.nombre, dni: driver.dni, email: driver.email,
    phone: driver.telefono, accountStatus: driver.estado_usuario, configured: driver.perfil_configurado,
    branch: driver.sucursal_base ? mapBranch(driver.sucursal_base) : null,
    distanceType: driver.tipo_reparto, active: driver.activo, available: driver.disponible_para_recorridos }
}

export function mapSummary(route: ApiRouteSummary): DeliveryRouteSummary {
  return { id: route.id, date: route.fecha, distanceType: route.tipo_distancia, status: route.estado,
    automatic: route.generado_automaticamente, branchId: route.sucursal_origen_id, branchName: route.sucursal_origen_nombre,
    driver: { id: route.repartidor.usuario_id, name: route.repartidor.nombre, phone: route.repartidor.telefono },
    stopCount: route.cantidad_paradas, packageCount: route.cantidad_paquetes,
    distanceKm: route.distancia_estimada_km, durationMinutes: route.duracion_estimada_min,
    createdAt: route.created_at, updatedAt: route.updated_at }
}

export function mapRoute(route: ApiRouteDetail): DeliveryRoute {
  return { ...mapSummary(route), streetOrientation: route.orientacion_calles_grados,
    returnsToBranch: route.vuelve_a_sucursal, branch: mapBranch(route.sucursal_origen),
    packagesWithoutLocation: route.paquetes_sin_ubicacion,
    path: route.trazado.map((point) => ({ latitude: point.latitud, longitude: point.longitud })),
    stops: route.paradas.map((stop) => ({ order: stop.orden, type: stop.tipo_parada,
      destination: stop.destino, latitude: stop.latitud, longitude: stop.longitud,
      packages: stop.paquetes.map((item) => ({ id: item.paquete_id, code: item.numero_paquete,
        order: item.orden, description: item.descripcion, weightKg: item.peso_kg, status: item.estado,
        routeStatus: item.estado_en_recorrido, trackingToken: item.token_seguimiento,
        recipientName: item.destinatario_nombre, recipientPhone: item.destinatario_telefono })) })),
  }
}

function mapAlert(alert: ApiRouteAlert): RouteAlert {
  return { id: alert.id, packageId: alert.paquete_id, packageNumber: alert.numero_paquete,
    trackingToken: alert.token_seguimiento, destination: alert.destino, reason: alert.motivo,
    description: alert.descripcion_motivo, branchId: alert.sucursal_actual_id,
    routeId: alert.recorrido_id, resolved: alert.resuelta, createdAt: alert.created_at }
}

export async function getDrivers(token: string, signal?: AbortSignal): Promise<Driver[]> {
  const result = await request<ApiDriver[]>('/repartidores', token, { signal })
  if (!Array.isArray(result.data)) throw new RoutesApiError('No pudimos leer los repartidores. Intentá nuevamente.')
  return result.data.map(mapDriver)
}

export async function saveDriverProfile(input: DriverProfileInput, token: string): Promise<Driver> {
  const result = await request<ApiDriver>(`/repartidores/${encodeURIComponent(input.driverId)}/perfil`, token, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sucursal_base_id: input.branchId, tipo_reparto: input.distanceType, activo: input.active }),
  })
  return mapDriver(result.data)
}

export async function getRoutes(filters: RouteFilters, token: string, signal?: AbortSignal): Promise<DeliveryRouteSummary[]> {
  const params = new URLSearchParams({ fecha: filters.date, tipo_distancia: filters.distanceType })
  if (filters.branchId) params.set('sucursal_id', String(filters.branchId))
  const result = await request<ApiRouteSummary[]>(`/recorridos?${params}`, token, { signal })
  if (!Array.isArray(result.data)) throw new RoutesApiError('No pudimos leer los recorridos. Intentá nuevamente.')
  return result.data.map(mapSummary)
}

export async function getRoute(id: string, token: string, signal?: AbortSignal): Promise<DeliveryRoute> {
  const result = await request<ApiRouteDetail>(`/recorridos/${encodeURIComponent(id)}`, token, { signal })
  return mapRoute(result.data)
}

export async function getRouteAlerts(branchId: number, token: string, signal?: AbortSignal): Promise<RouteAlert[]> {
  const query = branchId ? `?sucursal_id=${branchId}` : ''
  const result = await request<ApiRouteAlert[]>(`/recorridos/alertas${query}`, token, { signal })
  if (!Array.isArray(result.data)) throw new RoutesApiError('No pudimos leer las alertas. Intentá nuevamente.')
  return result.data.map(mapAlert)
}

export async function resolveRouteAlert(id: string, token: string): Promise<RouteAlert> {
  const result = await request<ApiRouteAlert>(`/recorridos/alertas/${encodeURIComponent(id)}/resolver`, token, { method: 'PATCH' })
  return mapAlert(result.data)
}

export async function generateRoutes(input: GenerateRoutesInput, token: string): Promise<GenerationResult> {
  const result = await request<ApiGeneration>('/recorridos/generar', token, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sucursal_id: input.branchId, fecha: input.date, tipo_distancia: input.distanceType,
      orientacion_calles_grados: input.streetOrientation, repartidor_ids: input.driverIds,
      reemplazar_existentes: input.replaceExisting }),
  })
  const summary = result.data.resumen
  return { message: result.message || 'Planificación generada.',
    summary: { pending: summary.paquetes_pendientes, assigned: summary.paquetes_asignados,
      unassigned: summary.paquetes_sin_recorrido, drivers: summary.repartidores_disponibles,
      generated: summary.recorridos_generados, replaced: summary.recorridos_reemplazados },
    routes: result.data.recorridos.map(mapRoute), alerts: result.data.alertas.map(mapAlert) }
}

export async function runRouteCommand(command: RouteCommand, token: string): Promise<RouteUpdate> {
  const root = `/recorridos/${encodeURIComponent(command.id)}`
  const options: RequestInit = { method: 'POST' }
  let path = root
  if (command.action === 'save') {
    path += '/paquetes'
    options.method = 'PUT'
    options.body = JSON.stringify({ paquetes: command.packages })
  } else if (command.action === 'locate') {
    path += `/paquetes/${encodeURIComponent(command.packageCode)}/ubicacion`
    options.method = 'PATCH'
    options.body = JSON.stringify({ latitud: command.latitude, longitud: command.longitude })
  } else if (command.action === 'assign') {
    path += '/repartidor'
    options.method = 'PATCH'
    options.body = JSON.stringify({ repartidor_id: command.driverId })
  } else if (command.action === 'delete') options.method = 'DELETE'
  else path += command.action === 'start' ? '/iniciar' : '/optimizar'
  if (options.body) options.headers = { 'Content-Type': 'application/json' }
  const result = await request<ApiRouteDetail>(path, token, options)
  return { route: command.action === 'delete' ? null : mapRoute(result.data),
    message: result.message || 'Recorrido actualizado.', alerts: (result.alertas ?? []).map(mapAlert) }
}
