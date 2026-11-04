export type NotificationChannel = 'EMAIL' | 'WHATSAPP'
export type NotificationStatus = 'PENDIENTE' | 'ENVIADO' | 'FALLIDO'
/** Hito del envío que originó el aviso. */
export type NotificationReason =
  | 'NUEVO_ENVIO' | 'ADMITIDO' | 'EN_REPARTO' | 'LISTO_PARA_RETIRO'
  | 'ENTREGADO' | 'VISITA_FALLIDA' | 'DEVOLUCION' | 'VENCIDO'

export interface ApiShipmentNotification {
  id: string
  motivo: NotificationReason
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
  reason: NotificationReason
  channel: NotificationChannel
  recipient: 'REMITENTE' | 'DESTINATARIO'
  destination: string
  status: NotificationStatus
  error: string | null
  updatedAt: string
}
