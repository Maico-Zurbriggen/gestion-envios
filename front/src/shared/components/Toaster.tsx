import { useSyncExternalStore } from 'react'
import { CircleAlert, CircleCheck, X } from 'lucide-react'
import { dismissToast, getToasts, subscribeToasts } from '../services/toast'

export function Toaster() {
  const items = useSyncExternalStore(subscribeToasts, getToasts)
  return (
    <div className="toaster" role="status" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={`toast toast--${item.tone}`}>
          {item.tone === 'success' ? <CircleCheck size={18} aria-hidden="true" /> : <CircleAlert size={18} aria-hidden="true" />}
          <p>{item.message}</p>
          <button type="button" aria-label="Cerrar aviso" onClick={() => dismissToast(item.id)}>
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  )
}
