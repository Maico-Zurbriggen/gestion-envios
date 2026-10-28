import { useEffect, useEffectEvent, useRef, useState } from 'react'
import {
  checkCameraAvailability,
  classifyCameraError,
  setTorch,
  startBarcodeScan,
  trackSupportsTorch,
  type BarcodeScan,
  type CameraErrorKind,
} from '../services/barcodeScanner'
import { isRepeatedRead, normalizeScannedCode, type LastRead } from '../services/scannedCode'

export type CameraScannerStatus = 'starting' | 'scanning' | 'error'

/** `'stop'` deja de analizar cuadros (por ejemplo, en el modo de lectura única). */
export type CameraReadResult = 'stop' | void

/**
 * Abre la cámara trasera mientras el componente está montado, la conecta al
 * `<video>` de `videoRef` y avisa cada código leído por `onRead`, ya
 * normalizado y sin repeticiones: el mismo código se ignora mientras siga en
 * cuadro y hasta 2,5 s después.
 *
 * Cerrar tiene que apagar la cámara: si las pistas no se detienen, la luz
 * queda prendida y el teléfono sigue gastando batería. Toda la limpieza está
 * en `stopAll`, que corre al desmontar y en cualquier error, incluida la
 * carrera de cerrar mientras el navegador todavía pide el permiso.
 */
export function useCameraScanner(onRead: (code: string) => CameraReadResult) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const trackRef = useRef<MediaStreamTrack | null>(null)
  const unavailable = checkCameraAvailability()
  const [status, setStatus] = useState<CameraScannerStatus>(unavailable ? 'error' : 'starting')
  const [error, setError] = useState<CameraErrorKind | null>(unavailable)
  const [torchAvailable, setTorchAvailable] = useState(false)
  const [torchOn, setTorchOn] = useState(false)

  // Evento de efecto: lee siempre el `onRead` más reciente sin que el efecto
  // dependa de él (si dependiera, cada render del padre reabriría la cámara).
  const handleRead = useEffectEvent((code: string) => onRead(code))

  useEffect(() => {
    if (checkCameraAvailability()) return
    let cancelled = false
    let stream: MediaStream | null = null
    let scan: BarcodeScan | null = null
    let reading = true
    let last: LastRead | null = null

    const onDetect = (raw: string) => {
      if (cancelled || !reading) return
      const code = normalizeScannedCode(raw)
      if (!code) return
      const now = Date.now()
      const repeated = isRepeatedRead(code, last, now)
      last = { code, at: now }
      if (repeated) return
      if (handleRead(code) === 'stop') {
        reading = false
        scan?.stop()
      }
    }

    const stopAll = () => {
      cancelled = true
      scan?.stop()
      scan = null
      // Detener cada pista es lo que apaga la cámara de verdad.
      stream?.getTracks().forEach((track) => track.stop())
      stream = null
      trackRef.current = null
      const video = videoRef.current
      if (video) video.srcObject = null
    }

    const start = async () => {
      try {
        const opened = await navigator.mediaDevices.getUserMedia({
          // `environment` es la cámara trasera; sin esto muchos teléfonos abren la frontal.
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        })
        // Se cerró mientras se pedía el permiso: apagar lo que acaba de abrirse.
        if (cancelled) {
          opened.getTracks().forEach((track) => track.stop())
          return
        }
        stream = opened
        const video = videoRef.current
        if (!video) {
          stopAll()
          return
        }
        video.srcObject = opened
        await video.play()
        if (cancelled) return

        const track = opened.getVideoTracks()[0] ?? null
        trackRef.current = track
        setTorchAvailable(trackSupportsTorch(track))

        const started = await startBarcodeScan(video, opened, onDetect)
        if (cancelled || !reading) {
          started.stop()
          if (cancelled) return
        }
        scan = started
        setStatus('scanning')
      } catch (cause) {
        if (cancelled) return
        stopAll()
        setError(classifyCameraError(cause))
        setStatus('error')
      }
    }

    void start()
    return stopAll
  }, [])

  async function toggleTorch() {
    const track = trackRef.current
    if (!track) return
    const next = !torchOn
    try {
      await setTorch(track, next)
      setTorchOn(next)
    } catch {
      // Algunos equipos anuncian la linterna pero no la dejan encender.
      setTorchAvailable(false)
    }
  }

  return { videoRef, status, error, torchAvailable, torchOn, toggleTorch }
}
