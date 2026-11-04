import { useEffect, useId, useRef } from 'react'
import { Check, CircleAlert, LoaderCircle, X } from 'lucide-react'
import '../routes.css'

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
  const descriptionId = useId()
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return <dialog ref={ref} className="modal modal--narrow route-confirm" aria-labelledby={titleId} aria-describedby={descriptionId} onCancel={(event) => { event.preventDefault(); if (!pending) onCancel() }}>
    <header className="modal__header">
      <span className="modal__icon" aria-hidden="true"><CircleAlert size={20} /></span>
      <div className="modal__titles">
        <h2 className="modal__title" id={titleId}>{title}</h2>
        <p className="modal__description" id={descriptionId}>{description}</p>
      </div>
    </header>
    <footer className="modal__footer">
      <button className="route-button" type="button" disabled={pending} onClick={onCancel} autoFocus><X size={17} aria-hidden="true" /> Cancelar</button>
      <button className="route-button route-button--primary" type="button" disabled={pending} onClick={onConfirm}>
        {pending ? <LoaderCircle size={17} className="loading-icon" aria-hidden="true" /> : <Check size={17} aria-hidden="true" />}{pending ? 'Procesando…' : confirmLabel}
      </button>
    </footer>
  </dialog>
}
