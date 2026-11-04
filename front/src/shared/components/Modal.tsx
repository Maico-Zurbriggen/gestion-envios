import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X, type LucideIcon } from 'lucide-react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: ReactNode
  eyebrow?: string
  description?: ReactNode
  icon?: LucideIcon
  size?: 'narrow' | 'default' | 'wide'
  footer?: ReactNode
  children: ReactNode
  className?: string
}

/**
 * Ventana modal accesible sobre `<dialog>`: el navegador mantiene el foco
 * adentro, cierra con Escape y deja el resto de la pantalla inerte.
 * El contenido se monta solo mientras está abierta.
 */
export function Modal({
  open,
  onClose,
  title,
  eyebrow,
  description,
  icon: Icon,
  size = 'default',
  footer,
  children,
  className = '',
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      // Sin un campo con autoFocus, el navegador enfoca la X y en el celular se dibuja su anillo
      // de foco al abrir. El foco queda en la ventana; con Tab se llega a la X como siempre.
      if (document.activeElement instanceof HTMLElement && document.activeElement.classList.contains('modal__close')) {
        dialog.focus()
      }
    }
    if (!open && dialog.open) dialog.close()
  }, [open])

  useEffect(() => {
    if (!open) return
    const previous = document.documentElement.style.overflow
    document.documentElement.style.overflow = 'hidden'
    return () => {
      document.documentElement.style.overflow = previous
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      className={`modal ${size !== 'default' ? `modal--${size}` : ''} ${className}`.trim()}
      tabIndex={-1}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      {open ? (
        <>
          <header className="modal__header">
            {Icon ? (
              <span className="modal__icon" aria-hidden="true">
                <Icon size={20} />
              </span>
            ) : null}
            <div className="modal__titles">
              {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
              <h2 className="modal__title" id={titleId}>
                {title}
              </h2>
              {description ? (
                <p className="modal__description" id={descriptionId}>
                  {description}
                </p>
              ) : null}
            </div>
            <button className="modal__close" type="button" aria-label="Cerrar" onClick={onClose}>
              <X size={20} aria-hidden="true" />
            </button>
          </header>
          <div className="modal__body">{children}</div>
          {footer ? <footer className="modal__footer">{footer}</footer> : null}
        </>
      ) : null}
    </dialog>
  )
}
