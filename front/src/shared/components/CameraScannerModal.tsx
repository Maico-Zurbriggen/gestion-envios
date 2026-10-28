import { useState } from 'react'
import { Camera, CircleAlert, CircleCheck, Flashlight, FlashlightOff, LoaderCircle, X } from 'lucide-react'
import { Modal } from './Modal'
import { useCameraScanner, type CameraReadResult } from '../hooks/useCameraScanner'
import type { CameraErrorKind } from '../services/barcodeScanner'
import { checkScannedCode } from '../services/scannedCode'
import './CameraScannerModal.css'

export type CameraScanMode = 'single' | 'continuous'

/**
 * Resultado de procesar un código: nada si se aceptó, o un mensaje para la
 * persona si la pantalla lo rechaza (por ejemplo, un paquete que no es del
 * recorrido). Un código rechazado no cierra la cámara.
 */
export type CameraScanHandler = (code: string) => string | void

export interface CameraScannerModalProps {
  mode: CameraScanMode
  onScan: CameraScanHandler
  onClose: () => void
  /** Formato que debe cumplir el código antes de entregarlo a la pantalla. */
  pattern?: RegExp
  /** Mensaje para un código que no cumple `pattern`. */
  patternMessage?: (code: string) => string
  title?: string
  description?: string
  /** Aclaración que se muestra debajo de la lista en el modo continuo. */
  continuousHint?: string
}

const ERROR_MESSAGES: Record<CameraErrorKind, { title: string; detail: string }> = {
  'sin-https': {
    title: 'La cámara necesita una conexión segura',
    detail: 'El navegador solo habilita la cámara por HTTPS. Entrando por la dirección IP de la red local con HTTP no funciona. Mientras tanto, escribí el código a mano o usá el lector.',
  },
  'sin-soporte': {
    title: 'Este navegador no puede abrir la cámara',
    detail: 'Probá con Chrome en Android o Safari en iPhone, o usá el lector de códigos.',
  },
  'permiso-denegado': {
    title: 'Falta el permiso de cámara',
    detail: 'El navegador tiene bloqueada la cámara para este sitio. Habilitala desde el candado de la barra de direcciones (permisos del sitio) y volvé a abrir el escáner.',
  },
  'sin-camara': {
    title: 'No encontramos una cámara',
    detail: 'El dispositivo no tiene una cámara disponible. Escribí el código a mano o usá el lector.',
  },
  'en-uso': {
    title: 'La cámara está ocupada',
    detail: 'Otra aplicación o pestaña está usando la cámara. Cerrala y volvé a abrir el escáner.',
  },
  desconocido: {
    title: 'No se pudo encender la cámara',
    detail: 'Volvé a intentarlo. Si sigue fallando, escribí el código a mano.',
  },
}

const MAX_RECENT_READS = 6

interface Feedback {
  tone: 'success' | 'error'
  text: string
}

interface RecentRead {
  id: string
  code: string
  time: string
}

function vibrate(pattern: number | number[]) {
  try {
    navigator.vibrate?.(pattern)
  } catch {
    /* sin vibración disponible */
  }
}

const timeFormatter = new Intl.DateTimeFormat('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

/**
 * Lector de códigos con la cámara del teléfono. Se monta solo mientras está
 * abierto: al desmontarse apaga la cámara.
 *
 * - Modo único: lee, vibra, entrega el código y se cierra.
 * - Modo continuo: queda abierto, cada lectura se entrega a la pantalla y se
 *   lista entre los últimos códigos leídos.
 */
export function CameraScannerModal({
  mode,
  onScan,
  onClose,
  pattern,
  patternMessage = (code) => `El código ${code} no tiene el formato esperado.`,
  title = 'Escanear con la cámara',
  description = 'Apuntá la cámara trasera al código de barras de la etiqueta. La lectura es automática.',
  continuousHint,
}: CameraScannerModalProps) {
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [recent, setRecent] = useState<RecentRead[]>([])

  function handleRead(code: string): CameraReadResult {
    const check = checkScannedCode(code, pattern)
    if (!check.valid) {
      if (check.reason === 'pattern') {
        vibrate([40, 60, 40])
        setFeedback({ tone: 'error', text: patternMessage(check.code) })
      }
      return
    }
    const rejection = onScan(check.code)
    if (rejection) {
      vibrate([40, 60, 40])
      setFeedback({ tone: 'error', text: rejection })
      return
    }
    // La vibración confirma la lectura sin obligar a mirar la pantalla.
    vibrate(80)
    if (mode === 'single') {
      onClose()
      return 'stop'
    }
    const now = new Date()
    setRecent((items) => [{ id: `${check.code}-${now.getTime()}`, code: check.code, time: timeFormatter.format(now) }, ...items].slice(0, MAX_RECENT_READS))
    setFeedback({ tone: 'success', text: `${check.code} leído. Podés apuntar al siguiente.` })
  }

  const { videoRef, status, error, torchAvailable, torchOn, toggleTorch } = useCameraScanner(handleRead)
  const message = error ? ERROR_MESSAGES[error] : null
  const TorchIcon = torchOn ? FlashlightOff : Flashlight

  return (
    <Modal
      open
      onClose={onClose}
      title={title}
      eyebrow={mode === 'continuous' ? 'Lectura continua' : 'Lector con cámara'}
      description={description}
      icon={Camera}
      className="camera-scanner"
      footer={<>
        {torchAvailable && status === 'scanning' && (
          <button className="btn" type="button" aria-pressed={torchOn} onClick={() => void toggleTorch()}>
            <TorchIcon size={18} aria-hidden="true" /> Linterna
          </button>
        )}
        <button className={`btn${mode === 'continuous' && recent.length > 0 ? ' btn--primary' : ''}`} type="button" onClick={onClose}>
          <X size={18} aria-hidden="true" /> {mode === 'continuous' ? 'Cerrar cámara' : 'Cancelar'}
        </button>
      </>}
    >
      <div className="camera-scanner__content">
        {message ? (
          <div className="form-error camera-scanner__error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            <span><strong>{message.title}</strong>{message.detail}</span>
          </div>
        ) : (
          <div className="camera-scanner__viewport">
            <video ref={videoRef} className="camera-scanner__video" playsInline muted aria-label="Vista de la cámara" />
            {/* Guía visual ancha y baja, con la forma de un Code 128: no recorta nada. */}
            <div className="camera-scanner__guide" aria-hidden="true"><span /></div>
            {status === 'starting' && (
              <div className="camera-scanner__overlay" role="status">
                <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> Encendiendo la cámara…
              </div>
            )}
          </div>
        )}

        <p className={`camera-scanner__feedback${feedback ? ` camera-scanner__feedback--${feedback.tone}` : ''}`} role="status" aria-live="polite">
          {feedback ? <>
            {feedback.tone === 'error' ? <CircleAlert size={18} aria-hidden="true" /> : <CircleCheck size={18} aria-hidden="true" />}
            {feedback.text}
          </> : status === 'scanning' ? 'Centrá el código dentro del recuadro y mantené el teléfono quieto.' : null}
        </p>

        {mode === 'continuous' && !message && (
          <section className="camera-scanner__recent" aria-labelledby="camera-scanner-recent-title">
            <h3 id="camera-scanner-recent-title">Últimos leídos</h3>
            {recent.length === 0 ? <p className="camera-scanner__empty">Todavía no se leyó ningún código.</p> : (
              <ol>
                {recent.map((item) => <li key={item.id}><strong>{item.code}</strong><span>{item.time}</span></li>)}
              </ol>
            )}
            {continuousHint && <p className="camera-scanner__hint">{continuousHint}</p>}
          </section>
        )}
      </div>
    </Modal>
  )
}
