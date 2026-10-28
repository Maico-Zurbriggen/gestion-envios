import { useRef, useState } from 'react'
import { Camera } from 'lucide-react'
import { checkCameraAvailability } from '../services/barcodeScanner'
import { CameraScannerModal, type CameraScannerModalProps } from './CameraScannerModal'

interface ScanWithCameraButtonProps extends Omit<CameraScannerModalProps, 'onClose'> {
  /** Texto visible del botón. */
  label?: string
  className?: string
  disabled?: boolean
}

/**
 * Botón que abre el lector con cámara. Solo aparece donde puede funcionar:
 * ofrecerlo para que al tocarlo diga "no se puede" es peor que no mostrarlo
 * (sin HTTPS el navegador ni siquiera pide el permiso).
 */
export function ScanWithCameraButton({ label = 'Escanear con cámara', className = 'ops-button', disabled = false, ...scanner }: ScanWithCameraButtonProps) {
  const [open, setOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  if (checkCameraAvailability() !== null) return null

  function close() {
    setOpen(false)
    // El modal se desmonta al cerrarse: si el foco quedó perdido vuelve al
    // botón; si la pantalla ya lo movió (por ejemplo, a un formulario nuevo), se respeta.
    requestAnimationFrame(() => {
      const active = document.activeElement
      if (!active || active === document.body) buttonRef.current?.focus()
    })
  }

  return <>
    <button ref={buttonRef} className={`${className} scan-camera-button`} type="button" aria-haspopup="dialog" disabled={disabled} onClick={() => setOpen(true)}>
      <Camera size={18} aria-hidden="true" /> {label}
    </button>
    {open && <CameraScannerModal {...scanner} onClose={close} />}
  </>
}
