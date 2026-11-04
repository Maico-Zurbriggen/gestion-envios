import { PackageSearch } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { selectCurrentUser } from '../../auth/redux/authSlice'

const MONITOR_ROLES = new Set(['ADMINISTRATIVO', 'SUPERADMIN'])

/**
 * Acceso a la trazabilidad de un paquete desde cualquier pantalla operativa.
 * Solo se muestra a quien puede entrar al monitor.
 */
export function TraceLink({ code, className = 'trace-link', label = 'Ver trazabilidad' }: { code: string; className?: string; label?: string }) {
  const user = useAppSelector(selectCurrentUser)
  if (!user?.role || !MONITOR_ROLES.has(user.role)) return null
  return (
    <Link className={className} to={`/monitor/trazabilidad/${code}`} title={`Ver todo lo que pasó con ${code}`}>
      <PackageSearch size={16} aria-hidden="true" />
      {label}
    </Link>
  )
}
