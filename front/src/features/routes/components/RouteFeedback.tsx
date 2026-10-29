import { CircleAlert, LoaderCircle, RefreshCw } from 'lucide-react'
import '../routes.css'

export function RouteError({ error, onRetry, pending = false }: { error: Error; onRetry?: () => void; pending?: boolean }) {
  return <div className="route-feedback route-feedback--error" role="alert">
    <CircleAlert size={20} aria-hidden="true" /><div><p>{error.message}</p>
      {onRetry && <button className="route-button" type="button" disabled={pending} onClick={onRetry}><RefreshCw size={16} aria-hidden="true" /> Reintentar</button>}
    </div>
  </div>
}

export function RouteLoading({ label }: { label: string }) {
  return <p className="route-feedback" role="status"><LoaderCircle className="loading-icon" size={21} aria-hidden="true" /> {label}</p>
}
