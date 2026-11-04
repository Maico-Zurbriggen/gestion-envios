/**
 * Lectura de códigos con la cámara del dispositivo (portado de "Administrador
 * Stock Tekron").
 *
 * Dado un `<video>` que ya muestra la cámara, avisa cuando aparece un código
 * en el cuadro. No pide permisos ni dibuja nada: de eso se ocupa
 * `useCameraScanner`.
 *
 * Hay dos caminos. Chrome en Android trae `BarcodeDetector`, nativo y sin
 * peso extra. Safari (iPhone y Mac) no lo tiene: ahí se usa ZXing, que se
 * descarga con `import()` dinámico solo cuando hace falta, en un archivo
 * aparte que Vite separa solo.
 */

/**
 * Formatos que se piden al detector nativo. La lista es corta a propósito:
 * cuantos más formatos, más trabajo por cuadro. Las etiquetas usan Code 128;
 * QR, Code 39 y EAN-13 cubren etiquetas de terceros.
 */
const NATIVE_BARCODE_FORMATS = ['code_128', 'qr_code', 'code_39', 'ean_13'] as const

/** Por qué no se puede usar la cámara. Cada motivo tiene una salida distinta. */
export type CameraUnavailableReason = 'sin-https' | 'sin-soporte'

/**
 * Revisa si el navegador puede abrir la cámara (`revisarDisponibilidadCamara`
 * en Tekron). `getUserMedia` solo existe en un contexto seguro (HTTPS o
 * `localhost`): entrando por la IP de la red local con HTTP el navegador ni
 * siquiera pregunta y parece que el teléfono no tuviera cámara.
 */
export function checkCameraAvailability(): CameraUnavailableReason | null {
  if (typeof window === 'undefined') return 'sin-soporte'
  if (!window.isSecureContext) return 'sin-https'
  if (!navigator.mediaDevices?.getUserMedia) return 'sin-soporte'
  return null
}

/** Lectura en curso. Hay que llamar a `stop` siempre, aun si algo falló. */
export interface BarcodeScan {
  stop: () => void
}

/** Forma mínima de `BarcodeDetector`, que TypeScript todavía no declara. */
interface NativeDetector {
  detect: (source: CanvasImageSource) => Promise<Array<{ rawValue: string }>>
}

interface NativeDetectorConstructor {
  new (options?: { formats?: readonly string[] }): NativeDetector
  getSupportedFormats?: () => Promise<string[]>
}

/**
 * Cada cuánto se analiza un cuadro: unas 6-7 veces por segundo alcanzan para
 * enganchar apenas se apunta bien, sin dejar el procesador al máximo.
 */
const DETECTION_INTERVAL_MS = 150

async function createNativeDetector(): Promise<NativeDetector | null> {
  const Detector = (window as unknown as { BarcodeDetector?: NativeDetectorConstructor }).BarcodeDetector
  if (typeof Detector !== 'function') return null
  try {
    // Algunos Chrome de escritorio exponen la API sin soporte real de Code 128:
    // en ese caso conviene ZXing antes que una cámara que nunca lee nada.
    const supported = await Detector.getSupportedFormats?.()
    const formats = supported ? NATIVE_BARCODE_FORMATS.filter((format) => supported.includes(format)) : [...NATIVE_BARCODE_FORMATS]
    if (!formats.includes('code_128')) return null
    return new Detector({ formats })
  } catch {
    return null
  }
}

function startNativeScan(detector: NativeDetector, video: HTMLVideoElement, onDetect: (code: string) => void): BarcodeScan {
  let active = true
  let busy = false
  const timer = window.setInterval(() => {
    // Antes del primer cuadro el video mide 0x0 y el detector falla.
    if (!active || busy || video.videoWidth === 0 || video.videoHeight === 0) return
    busy = true
    detector
      .detect(video)
      .then((found) => {
        const code = found[0]?.rawValue?.trim()
        if (active && code) onDetect(code)
      })
      // Un cuadro ilegible no es un error: el siguiente intento llega enseguida.
      .catch(() => undefined)
      .finally(() => { busy = false })
  }, DETECTION_INTERVAL_MS)
  return {
    stop: () => {
      active = false
      window.clearInterval(timer)
    },
  }
}

async function startZxingScan(video: HTMLVideoElement, stream: MediaStream, onDetect: (code: string) => void): Promise<BarcodeScan> {
  const [{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType }] = await Promise.all([
    import('@zxing/browser'),
    import('@zxing/library'),
  ])
  // Limitar los formatos evita que ZXing pruebe una docena de lectores por cuadro.
  const hints = new Map<number, unknown>([[DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.CODE_128, BarcodeFormat.QR_CODE]]])
  const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: DETECTION_INTERVAL_MS })
  let active = true
  const controls = await reader.decodeFromStream(stream, video, (result) => {
    const code = result?.getText().trim()
    if (active && code) onDetect(code)
  })
  return {
    stop: () => {
      active = false
      controls.stop()
    },
  }
}

/**
 * Empieza a buscar códigos en el video. `onDetect` puede dispararse varias
 * veces con el mismo código mientras siga en cuadro: quien llama decide.
 */
export async function startBarcodeScan(
  video: HTMLVideoElement,
  stream: MediaStream,
  onDetect: (code: string) => void,
): Promise<BarcodeScan> {
  const detector = await createNativeDetector()
  if (detector) return startNativeScan(detector, video, onDetect)
  return startZxingScan(video, stream, onDetect)
}

/** Linterna: no está en los tipos de DOM porque solo la exponen algunos navegadores. */
type TorchCapabilities = MediaTrackCapabilities & { torch?: boolean }

export function trackSupportsTorch(track: MediaStreamTrack | null): boolean {
  if (!track || typeof track.getCapabilities !== 'function') return false
  try {
    return Boolean((track.getCapabilities() as TorchCapabilities).torch)
  } catch {
    return false
  }
}

export function setTorch(track: MediaStreamTrack, on: boolean): Promise<void> {
  return track.applyConstraints({ advanced: [{ torch: on } as MediaTrackConstraintSet] })
}

/** Errores de cámara, cada uno con un mensaje y una salida concreta. */
export type CameraErrorKind = CameraUnavailableReason | 'permiso-denegado' | 'sin-camara' | 'en-uso' | 'desconocido'

export function classifyCameraError(error: unknown): CameraErrorKind {
  const name = error instanceof Error || error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') return 'permiso-denegado'
  if (name === 'NotFoundError' || name === 'OverconstrainedError' || name === 'DevicesNotFoundError') return 'sin-camara'
  if (name === 'NotReadableError' || name === 'TrackStartError' || name === 'AbortError') return 'en-uso'
  return 'desconocido'
}
