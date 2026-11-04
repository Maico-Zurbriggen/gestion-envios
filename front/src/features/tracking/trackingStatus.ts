export type TrackingDeliveryType = 'domicilio' | 'sucursal'

function normalizeStatus(status: string) {
  return status.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/\s+/g, '_')
}

// Llegar a la sucursal de destino es parte del viaje para un envío a domicilio,
// pero es la etapa "lista para retirar" cuando el destinatario lo busca en sucursal.
const HOME_STEPS: Record<string, number> = {
  PENDIENTE: 0, REGISTRADO: 0,
  EN_SUCURSAL: 1, EN_SUCURSAL_ORIGEN: 1,
  EN_TRANSITO: 2, EN_SUCURSAL_DESTINO: 2, EN_REPARTO: 2, EN_VIAJE: 2, ENTREGA_FALLIDA: 2,
  // Después de las visitas sin entrega queda esperando en la sucursal: sigue sin entregarse.
  LISTO_PARA_RETIRO: 2, EN_DEVOLUCION: 2,
  ENTREGADO: 3, ENTREGADO_EN_SUCURSAL: 3, RETIRADO: 3, DEVUELTO: 3,
}

const PICKUP_STEPS: Record<string, number> = {
  PENDIENTE: 0, REGISTRADO: 0,
  EN_SUCURSAL_ORIGEN: 1,
  EN_TRANSITO: 2, EN_VIAJE: 2,
  EN_SUCURSAL_DESTINO: 3, LISTO_PARA_RETIRO: 3, EN_SUCURSAL: 3, EN_DEVOLUCION: 3,
  ENTREGADO_EN_SUCURSAL: 4, RETIRADO: 4, ENTREGADO: 4, DEVUELTO: 4,
}

export function getStatusStep(status: string, deliveryType: TrackingDeliveryType = 'domicilio'): number {
  const steps = deliveryType === 'sucursal' ? PICKUP_STEPS : HOME_STEPS
  return steps[normalizeStatus(status)] ?? 0
}

const STATUS_LABELS: Record<string, string> = {
  PENDIENTE: 'Pendiente de ingreso',
  EN_SUCURSAL_ORIGEN: 'Recibido en terminal',
  EN_TRANSITO: 'En viaje',
  EN_SUCURSAL_DESTINO: 'En sucursal de destino',
  LISTO_PARA_RETIRO: 'Listo para retirar',
  EN_SUCURSAL: 'En sucursal',
  EN_REPARTO: 'En reparto',
  ENTREGADO: 'Entregado',
  ENTREGA_FALLIDA: 'Visita sin entrega',
  RETIRADO: 'Retirado',
  ENTREGADO_EN_SUCURSAL: 'Retirado en sucursal',
  EN_DEVOLUCION: 'Volviendo al remitente',
  DEVUELTO: 'Devuelto al remitente',
  VENCIDO: 'Vencido sin despachar',
}

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[normalizeStatus(status)] ?? status
}
