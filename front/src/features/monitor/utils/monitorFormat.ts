import {
  AlertTriangle,
  CircleCheckBig,
  Clock3,
  Package,
  Store,
  Truck,
  Warehouse,
  XCircle,
  type LucideIcon,
} from 'lucide-react'
import type { MonitorSummary, PackageGroup, Tone } from '../types/monitor.types'

export const GROUP_META: Record<PackageGroup, { label: string; icon: LucideIcon; tone: Tone }> = {
  PENDIENTES: { label: 'Pendientes de ingreso', icon: Clock3, tone: 'neutral' },
  EN_DEPOSITO: { label: 'En depósito', icon: Warehouse, tone: 'info' },
  EN_CAMINO: { label: 'En camino', icon: Truck, tone: 'brand' },
  PARA_RETIRAR: { label: 'Para retirar', icon: Store, tone: 'warning' },
  NO_ENTREGADOS: { label: 'Visita fallida', icon: XCircle, tone: 'danger' },
  ENTREGADOS: { label: 'Entregados', icon: CircleCheckBig, tone: 'success' },
  OTROS: { label: 'Otros', icon: Package, tone: 'neutral' },
}

/** Orden en que avanza un paquete, para la barra de flujo del panel general. */
export const PIPELINE: ReadonlyArray<Exclude<PackageGroup, 'OTROS'>> = [
  'PENDIENTES',
  'EN_DEPOSITO',
  'EN_CAMINO',
  'PARA_RETIRAR',
  'ENTREGADOS',
  'NO_ENTREGADOS',
]

export const INCIDENT_ICON = AlertTriangle

export const CLAIM_TYPE_LABELS: Record<string, string> = {
  DEMORA: 'Demora',
  DANIO: 'Daño',
  EXTRAVIO: 'Extravío',
  OTRO: 'Otro',
}

export const CLAIM_STATUS_META: Record<string, { label: string; badge: string; tone: Tone }> = {
  ABIERTO: { label: 'Abierto', badge: 'badge--warning', tone: 'warning' },
  EN_REVISION: { label: 'En revisión', badge: 'badge--info', tone: 'info' },
  RESUELTO: { label: 'Resuelto', badge: 'badge--success', tone: 'success' },
  RECHAZADO: { label: 'Rechazado', badge: 'badge--muted', tone: 'neutral' },
}

export const TONE_BADGE: Record<Tone, string> = {
  neutral: 'badge--muted',
  info: 'badge--info',
  brand: '',
  success: 'badge--success',
  warning: 'badge--warning',
  danger: 'badge--danger',
}

const dateTime = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
const dateOnly = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
const relative = new Intl.RelativeTimeFormat('es-AR', { numeric: 'auto' })

/** La API en SQLite devuelve fechas sin zona horaria: siempre son UTC. */
export function parseApiDate(value: string) {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`)
}

export function formatDateTime(value: string) {
  return dateTime.format(parseApiDate(value))
}

/** Fechas `YYYY-MM-DD` (día del recorrido) sin corrimiento por zona horaria. */
export function formatDay(value: string) {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return dateOnly.format(new Date(year, month - 1, day))
}

export function formatRelative(value: string, now = Date.now()) {
  const seconds = Math.round((parseApiDate(value).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'recién'
  if (abs < 3600) return relative.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return relative.format(Math.round(seconds / 3600), 'hour')
  if (abs < 86400 * 30) return relative.format(Math.round(seconds / 86400), 'day')
  return formatDateTime(value)
}

export function percent(part: number, total: number) {
  return total > 0 ? Math.round((part / total) * 100) : 0
}

/** Cantidad que acompaña a cada subsección en la barra interna. */
export function countForSection(id: string, summary: MonitorSummary | undefined): number | undefined {
  if (!summary) return undefined
  const counts: Record<string, number> = {
    'monitor-all': summary.totalPackages,
    'monitor-pending': summary.byGroup.PENDIENTES ?? 0,
    'monitor-warehouse': summary.byGroup.EN_DEPOSITO ?? 0,
    'monitor-transit': summary.byGroup.EN_CAMINO ?? 0,
    'monitor-pickup': summary.byGroup.PARA_RETIRAR ?? 0,
    'monitor-delivered': summary.byGroup.ENTREGADOS ?? 0,
    'monitor-incidents': summary.withProblems,
    'monitor-claims': summary.openClaims,
  }
  return counts[id]
}

