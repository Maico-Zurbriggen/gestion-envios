import { useEffect, useId, useRef } from 'react'
import { Check, LoaderCircle, X } from 'lucide-react'

export function ConfirmRouteAction({ title, description, confirmLabel, pending, onConfirm, onCancel }: {
  title: string
  description: string
  confirmLabel: string
  pending: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return <dialog ref={ref} className="route-confirm" aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); if (!pending) onCancel() }}>
    <h2 id={titleId}>{title}</h2><p>{description}</p>
    <div className="route-actions">
      <button className="route-button" type="button" disabled={pending} onClick={onCancel} autoFocus><X size={17} aria-hidden="true" /> Cancelar</button>
      <button className="route-button route-button--primary" type="button" disabled={pending} onClick={onConfirm}>
        {pending ? <LoaderCircle size={17} className="loading-icon" aria-hidden="true" /> : <Check size={17} aria-hidden="true" />}{pending ? 'Procesando…' : confirmLabel}
      </button>
    </div>
  </dialog>
}
