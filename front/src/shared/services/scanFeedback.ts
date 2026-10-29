/**
 * Aviso de lectura como en la caja del supermercado: un pitido limpio y agudo con una
 * vibración breve cuando el código se aceptó, y un zumbido grave cuando se rechazó.
 *
 * El sonido es un WAV generado acá y reproducido con `<audio>`: en iPhone, Web Audio
 * queda mudo con la tecla de silencio y `<audio>` no. Los navegadores solo dejan sonar
 * lo que se habilitó con un toque de la persona: `primeScanFeedback` va en el clic que
 * abre la cámara y "desbloquea" cada sonido reproduciéndolo en silencio.
 *
 * Vibración: `navigator.vibrate` en Android. Safari no lo tiene; en iOS 18 o posterior
 * se usa el toque háptico que hace el sistema al cambiar un interruptor (`switch`).
 */

type Wave = 'sine' | 'square'
type Note = [frequency: number, start: number, duration: number, wave: Wave]

const SAMPLE_RATE = 44100
// Elegidos entre las muestras: «Lector de caja» (tono limpio y agudo) y, para el rechazo, un zumbido grave.
const ACCEPTED: Note[] = [[2900, 0, 0.09, 'sine']]
const REJECTED: Note[] = [[180, 0, 0.3, 'square']]
// La onda cuadrada suena más fuerte a igual amplitud: se baja para que los dos se oigan parejo.
const LEVEL: Record<Wave, number> = { sine: 0.42, square: 0.22 }

const sounds: { accepted?: HTMLAudioElement; rejected?: HTMLAudioElement } = {}

/** WAV mono de 16 bits con las notas indicadas. */
function wav(notes: Note[]) {
  const seconds = Math.max(...notes.map(([, start, duration]) => start + duration)) + 0.03
  const length = Math.ceil(seconds * SAMPLE_RATE)
  const buffer = new ArrayBuffer(44 + length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => [...value].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)))
  text(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); text(8, 'WAVE')
  text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, SAMPLE_RATE, true); view.setUint32(28, SAMPLE_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  text(36, 'data'); view.setUint32(40, length * 2, true)
  for (let i = 0; i < length; i++) {
    const t = i / SAMPLE_RATE
    let sample = 0
    for (const [frequency, start, duration, wave] of notes) {
      if (t < start || t >= start + duration) continue
      const local = t - start
      // Entrada y salida suaves: sin "clics" al empezar y terminar.
      const envelope = Math.min(1, local / 0.004, (duration - local) / 0.006)
      const phase = frequency * local - Math.floor(frequency * local)
      const value = wave === 'square' ? (phase < 0.5 ? 1 : -1) : Math.sin(2 * Math.PI * phase)
      sample += value * envelope * LEVEL[wave]
    }
    view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, sample)) * 32767, true)
  }
  return URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }))
}

function unlock(audio: HTMLAudioElement) {
  audio.muted = true
  const restore = () => {
    audio.pause()
    audio.currentTime = 0
    audio.muted = false
  }
  audio.play().then(restore, () => { audio.muted = false })
}

/** Prepara y habilita los sonidos. Llamarlo dentro de un clic o toque. */
export function primeScanFeedback() {
  try {
    if (typeof Audio === 'undefined') return
    sounds.accepted ??= new Audio(wav(ACCEPTED))
    sounds.rejected ??= new Audio(wav(REJECTED))
    unlock(sounds.accepted)
    unlock(sounds.rejected)
  } catch {
    /* sin audio disponible */
  }
}

function play(audio: HTMLAudioElement | undefined) {
  if (!audio) return
  try {
    audio.currentTime = 0
    audio.play().catch(() => { /* el navegador no dejó sonar */ })
  } catch {
    /* sin audio disponible */
  }
}

/** Toque háptico de iOS: el sistema vibra al cambiar un `<input type="checkbox" switch>`. */
function iosTap() {
  // Con una ventana modal abierta el resto de la página está inerte: va dentro de ella.
  const host = document.querySelector('dialog[open]') ?? document.body
  const label = document.createElement('label')
  label.setAttribute('aria-hidden', 'true')
  label.style.display = 'none'
  const input = document.createElement('input')
  input.type = 'checkbox'
  input.setAttribute('switch', '')
  input.tabIndex = -1
  label.append(input)
  host.append(label)
  label.click()
  label.remove()
}

function vibrate(pattern: number[]) {
  try {
    if (typeof navigator.vibrate === 'function') {
      navigator.vibrate(pattern)
      return
    }
    // Un toque por cada pulso del patrón (los lugares pares son vibración).
    let at = 0
    pattern.forEach((ms, i) => {
      if (i % 2 === 0) setTimeout(iosTap, at)
      at += ms
    })
  } catch {
    /* sin vibración disponible */
  }
}

/** Código aceptado: «bip» corto y agudo, y una vibración breve. */
export function scanAccepted() {
  vibrate([80])
  play(sounds.accepted)
}

/** Código rechazado: zumbido grave y vibración doble. */
export function scanRejected() {
  vibrate([40, 60, 40])
  play(sounds.rejected)
}
