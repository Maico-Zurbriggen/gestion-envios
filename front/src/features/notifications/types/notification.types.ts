export type NotificationChannel = 'EMAIL' | 'WHATSAPP'
export type NotificationStatus = 'PENDIENTE' | 'ENVIADO' | 'FALLIDO'

export interface ApiShipmentNotification {
  id: string
  motivo: 'NUEVO_ENVIO' | 'VISITA_FALLIDA'
  canal: NotificationChannel
  destinatario_tipo: 'REMITENTE' | 'DESTINATARIO'
  destino: string
  estado: NotificationStatus
  error_detalle: string | null
  created_at: string
  updated_at: string
}

export interface ShipmentNotificationsResponse {
  status: 'success'
  message: string | null
  data: { token_seguimiento: string; notificaciones: ApiShipmentNotification[] }
}

export interface ShipmentNotification {
  id: string
  reason: 'NUEVO_ENVIO' | 'VISITA_FALLIDA'
  channel: NotificationChannel
  recipient: 'REMITENTE' | 'DESTINATARIO'
  destination: string
  status: NotificationStatus
  error: string | null
  updatedAt: string
}
