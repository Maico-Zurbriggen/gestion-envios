import { operationalRequest } from '../../../shared/services/operationalApi'
import type { ShipmentNotification, ShipmentNotificationsResponse } from '../types/notification.types'

const NOT_FOUND = 'No existe un envío con ese código de seguimiento.'

function mapNotifications(response: ShipmentNotificationsResponse): ShipmentNotification[] {
  if (!Array.isArray(response.data?.notificaciones)) throw new Error('No pudimos leer el estado de las notificaciones.')
  return response.data.notificaciones.map((item) => ({
    id: item.id,
    reason: item.motivo,
    channel: item.canal,
    recipient: item.destinatario_tipo,
    destination: item.destino,
    status: item.estado,
    error: item.error_detalle,
    updatedAt: item.updated_at,
  }))
}

export async function getShipmentNotifications(trackingToken: string, token: string, signal?: AbortSignal): Promise<ShipmentNotification[]> {
  const response = await operationalRequest<ShipmentNotificationsResponse>(
    `/envios/${encodeURIComponent(trackingToken)}/notificaciones`, token, { signal }, { notFound: NOT_FOUND },
  )
  return mapNotifications(response)
}

export async function retryShipmentNotifications(trackingToken: string, token: string): Promise<ShipmentNotification[]> {
  const response = await operationalRequest<ShipmentNotificationsResponse>(
    `/envios/${encodeURIComponent(trackingToken)}/notificaciones/reintentar`, token, { method: 'POST' }, { notFound: NOT_FOUND },
  )
  return mapNotifications(response)
}
