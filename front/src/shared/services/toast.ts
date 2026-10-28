export type ToastTone = 'success' | 'error'

export interface ToastItem {
  id: number
  tone: ToastTone
  message: string
}

let toasts: ToastItem[] = []
let nextId = 1
const listeners = new Set<() => void>()

function emit() {
  for (const listener of listeners) listener()
}

export function dismissToast(id: number) {
  toasts = toasts.filter((item) => item.id !== id)
  emit()
}

/** Aviso flotante breve (abajo a la derecha). Se cierra solo a los 4,5 s. */
export function showToast(message: string, tone: ToastTone = 'success') {
  const id = nextId++
  toasts = [...toasts.slice(-3), { id, tone, message }]
  emit()
  window.setTimeout(() => dismissToast(id), 4500)
}

export function subscribeToasts(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getToasts() {
  return toasts
}
