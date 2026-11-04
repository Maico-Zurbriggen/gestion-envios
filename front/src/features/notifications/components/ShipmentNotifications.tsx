import { CircleAlert, CircleCheck, Clock3, LoaderCircle, Mail, MessageCircle, RefreshCw, Send } from 'lucide-react'
import { useShipmentNotifications } from '../hooks/useShipmentNotifications'
import type { NotificationReason, ShipmentNotification } from '../types/notification.types'
import './ShipmentNotifications.css'

interface ShipmentNotificationsProps {
  trackingToken: string
}

const RECIPIENT_LABEL = { REMITENTE: 'Remitente', DESTINATARIO: 'Destinatario' } as const
const REASON_LABEL: Record<NotificationReason, string> = {
  NUEVO_ENVIO: 'Código de seguimiento',
  ADMITIDO: 'Admitido en sucursal',
  EN_REPARTO: 'Sale a reparto',
  LISTO_PARA_RETIRO: 'Listo para retirar',
  ENTREGADO: 'Entregado',
  VISITA_FALLIDA: 'Aviso de visita',
  DEVOLUCION: 'Devolución',
  VENCIDO: 'Registro vencido',
}

function StatusBadge({ item }: { item: ShipmentNotification }) {
  if (item.status === 'ENVIADO') return <span className="notification-status notification-status--ok"><CircleCheck size={15} aria-hidden="true" /> Enviado</span>
  if (item.status === 'PENDIENTE') return <span className="notification-status"><Clock3 size={15} aria-hidden="true" /> Pendiente</span>
  return <span className="notification-status notification-status--error"><CircleAlert size={15} aria-hidden="true" /> No enviado</span>
}

export function ShipmentNotifications({ trackingToken }: ShipmentNotificationsProps) {
  const { notifications, retry } = useShipmentNotifications(trackingToken)
  const items = notifications.data ?? []
  const retriable = items.some((item) => item.status !== 'ENVIADO')

  return (
    <section className="ops-panel ops-stack" aria-labelledby="shipment-notifications-title">
      <h2 id="shipment-notifications-title"><Send size={20} aria-hidden="true" /> Avisos al cliente</h2>
      <p className="ops-hint">Envío {trackingToken}: cada aviso que se mandó por email y WhatsApp (código de seguimiento, admisión, reparto, retiro, entrega y devolución).</p>
      {notifications.isPending && <p role="status"><LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> Consultando avisos…</p>}
      {notifications.isError && (
        <div className="form-error" role="alert">
          {notifications.error.message}
          <button className="ops-button" type="button" onClick={() => void notifications.refetch()}><RefreshCw size={18} aria-hidden="true" /> Reintentar consulta</button>
        </div>
      )}
      {notifications.isSuccess && !items.length && <p role="status">Este envío todavía no tiene avisos registrados.</p>}
      {items.length > 0 && (
        <ul className="notification-list" aria-live="polite">
          {items.map((item) => (
            <li key={item.id}>
              {item.channel === 'EMAIL' ? <Mail size={18} aria-hidden="true" /> : <MessageCircle size={18} aria-hidden="true" />}
              <div>
                <strong>{RECIPIENT_LABEL[item.recipient]} · {item.channel === 'EMAIL' ? 'Email' : 'WhatsApp'}</strong>
                <span className="ops-hint">{REASON_LABEL[item.reason] ?? item.reason} · {item.destination || 'Sin dato de contacto'}</span>
                {item.status === 'FALLIDO' && item.error && <span className="ops-hint">{item.error}</span>}
              </div>
              <StatusBadge item={item} />
            </li>
          ))}
        </ul>
      )}
      {retry.isError && <p className="form-error" role="alert">{retry.error.message}</p>}
      {retry.isSuccess && <p role="status">Se reintentaron los avisos pendientes o fallidos.</p>}
      {retriable && (
        <div className="ops-actions">
          <button className="ops-button" type="button" disabled={retry.isPending || notifications.isFetching} onClick={() => retry.mutate()}>
            {retry.isPending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <RefreshCw size={18} aria-hidden="true" />}
            {retry.isPending ? 'Reenviando…' : 'Reenviar avisos no enviados'}
          </button>
        </div>
      )}
    </section>
  )
}
