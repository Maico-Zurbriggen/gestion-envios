export function getStatusStep(status: string): number {
  const normalized = status.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/\s+/g, '_')
  const steps: Record<string, number> = {
    PENDIENTE: 0, REGISTRADO: 0,
    EN_SUCURSAL: 1, EN_SUCURSAL_ORIGEN: 1, EN_SUCURSAL_DESTINO: 1, LISTO_PARA_RETIRO: 1,
    EN_TRANSITO: 2, EN_REPARTO: 2, EN_VIAJE: 2, ENTREGA_FALLIDA: 2,
    ENTREGADO: 3, ENTREGADO_EN_SUCURSAL: 3, RETIRADO: 3,
  }
  return steps[normalized] ?? 0
}
