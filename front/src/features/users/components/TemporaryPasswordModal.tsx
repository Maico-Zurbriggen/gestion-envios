import { useState } from 'react'
import { Check, Clipboard, KeyRound } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'

interface TemporaryPasswordModalProps {
  result: { name: string; password: string; created: boolean } | null
  onClose: () => void
}

/** Muestra una única vez la contraseña temporal generada, con botón para copiarla. */
export function TemporaryPasswordModal({ result, onClose }: TemporaryPasswordModalProps) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.password)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  function close() {
    setCopied(false)
    onClose()
  }

  return (
    <Modal
      open={Boolean(result)}
      onClose={close}
      size="narrow"
      icon={KeyRound}
      eyebrow={result?.created ? 'Usuario registrado' : 'Contraseña blanqueada'}
      title="Contraseña temporal"
      description={result ? `Entregásela a ${result.name}. Deberá cambiarla en su primer ingreso.` : undefined}
      footer={
        <button className="btn btn--primary" type="button" onClick={close}>
          Listo
        </button>
      }
    >
      {result ? (
        <>
          <div className="temporary-password">
            <div>
              <span>Contraseña temporal</span>
              <strong>{result.password}</strong>
            </div>
            <button type="button" onClick={copy} aria-label="Copiar contraseña temporal">
              {copied ? <Check size={18} aria-hidden="true" /> : <Clipboard size={18} aria-hidden="true" />}
              {copied ? 'Copiada' : 'Copiar'}
            </button>
          </div>
          <p className="temporary-password__hint">
            Compartila por un canal seguro. Por seguridad no se vuelve a mostrar: si se pierde, blanqueala de nuevo.
          </p>
        </>
      ) : null}
    </Modal>
  )
}
