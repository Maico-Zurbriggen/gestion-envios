import { operationalRequest } from '../../../shared/services/operationalApi'
import { mapRoute, mapSummary } from '../../routes/services/routesApi'
import type { ApiRouteDetail, ApiRouteSummary } from '../../routes/types/route.types'
import type { ApiDeliveryReceipt, ApiDriverPosition, DeliveryOperation, DeliveryReceipt, DriverPosition, RecipientContact } from '../types/delivery.types'

const root = '/reparto/recorridos'
const routePath = (id: string) => `${root}/${encodeURIComponent(id)}`
function mapPosition(position: ApiDriverPosition | null): DriverPosition | null {
  return position ? { latitude: position.latitud, longitude: position.longitud, updatedAt: position.actualizado_at } : null
}
export async function getMyRoutes(date: string, status: string, token: string, signal?: AbortSignal) {
  const params = new URLSearchParams()
  if (date) params.set('fecha', date)
  if (status) params.set('estado', status)
  const { data } = await operationalRequest<{ data: ApiRouteSummary[] }>(`${root}?${params}`, token, { signal })
  if (!Array.isArray(data)) throw new Error('No pudimos leer tus recorridos.')
  return data.map(mapSummary)
}
export async function getMyRoute(id: string, token: string, signal?: AbortSignal) {
  const { data } = await operationalRequest<{ data: ApiRouteDetail }>(routePath(id), token, { signal })
  if (!data?.id || !Array.isArray(data.paradas)) throw new Error('No pudimos leer el recorrido.')
  return mapRoute(data)
}
export async function startMyRoute(id: string, token: string) {
  const { data } = await operationalRequest<{ data: ApiRouteDetail }>(`${routePath(id)}/iniciar`, token, { method: 'POST' })
  return mapRoute(data)
}
/** Mejor orden por calles de lo que falta, desde la ubicación del repartidor (si la comparte). */
export async function optimizeMyRoute(id: string, position: { latitude: number; longitude: number } | null, token: string) {
  const { data, message } = await operationalRequest<{ data: ApiRouteDetail; message: string | null }>(`${routePath(id)}/optimizar`, token, {
    method: 'POST', body: JSON.stringify(position ? { latitud: position.latitude, longitud: position.longitude } : {}),
  })
  return { route: mapRoute(data), message: message ?? 'Recorrido optimizado.' }
}

/** Llegada a la próxima sucursal de un recorrido entre sucursales, con la posición del celular si la comparte. */
export async function registerArrival(id: string, branchId: number, position: { latitude: number; longitude: number } | null, token: string) {
  const body = { sucursal_id: branchId, ...(position ? { latitud: position.latitude, longitud: position.longitude } : {}) }
  const { data, message } = await operationalRequest<{ data: ApiRouteDetail; message: string | null }>(`${routePath(id)}/llegadas`, token, {
    method: 'POST', body: JSON.stringify(body),
  })
  return { route: mapRoute(data), message: message ?? 'Llegada registrada.' }
}

export async function getPosition(id: string, token: string, signal?: AbortSignal) {
  const { data } = await operationalRequest<{ data: ApiDriverPosition | null }>(`${routePath(id)}/ubicacion`, token, { signal })
  return mapPosition(data)
}
export async function sendPosition(id: string, latitude: number, longitude: number, token: string, signal?: AbortSignal) {
  const result = await operationalRequest<{ data: ApiDriverPosition }>(`${routePath(id)}/ubicacion`, token, { method: 'PUT', body: JSON.stringify({ latitud: latitude, longitud: longitude }), signal })
  return { position: mapPosition(result.data) }
}
export async function getContact(id: string, code: string, token: string, signal?: AbortSignal): Promise<RecipientContact> {
  const { data } = await operationalRequest<{ data: { destinatario_nombre: string; telefono: string | null; telefono_disponible: boolean } }>(`${routePath(id)}/paquetes/${encodeURIComponent(code)}/contacto`, token, { signal })
  return { name: data.destinatario_nombre, phone: data.telefono_disponible ? data.telefono : null }
}
export async function registerDelivery(id: string, code: string, input: DeliveryOperation, token: string): Promise<DeliveryReceipt> {
  const body = input.action === 'failed' ? { operacion_id: input.operationId, motivo_fallo: input.reason } : {
    operacion_id: input.operationId, receptor_nombre: input.receiver.name, receptor_documento: input.receiver.document,
    receptor_fecha_nacimiento: input.receiver.birthDate, es_autorizado: input.receiver.authorized, firma_base64: input.receiver.signature,
  }
  const { data } = await operationalRequest<{ data: ApiDeliveryReceipt }>(`${routePath(id)}/paquetes/${encodeURIComponent(code)}/${input.action === 'failed' ? 'visita-fallida' : 'entrega'}`, token, { method: 'POST', body: JSON.stringify(body) })
  if (!data?.evento_id || !data.fecha_hora) throw new Error('No pudimos leer la constancia. Reintentá la misma operación para recuperar su resultado.')
  return { eventId: data.evento_id, packageId: data.paquete_id, result: data.resultado, receiverName: data.receptor_nombre, signatureAvailable: data.firma_disponible, occurredAt: data.fecha_hora }
}
