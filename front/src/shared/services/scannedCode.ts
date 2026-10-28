/**
 * Reglas puras para los códigos leídos con la cámara o el lector.
 * No dependen del navegador, así se prueban desde `tests/` con Node.
 */

/** Número de paquete público: `PAQ-` y diez caracteres alfanuméricos. */
export const PACKAGE_CODE_PATTERN = /^PAQ-[A-Z0-9]{10}$/i

/** Token de seguimiento del envío: `ENV-` y diez caracteres alfanuméricos. */
export const TRACKING_TOKEN_PATTERN = /^ENV-[A-Z0-9]{10}$/i

/** Tiempo durante el que se ignora una nueva lectura del mismo código. */
export const REPEATED_READ_WINDOW_MS = 2500

/** Deja el código como lo generan las etiquetas: en mayúsculas y sin espacios. */
export function normalizeScannedCode(raw: string): string {
  return raw.replace(/\s/g, '').toUpperCase()
}

export type ScannedCodeCheck =
  | { valid: true; code: string }
  | { valid: false; code: string; reason: 'empty' | 'pattern' }

/**
 * Normaliza el código y, si la pantalla lo pide, comprueba su formato
 * antes de aceptarlo.
 */
export function checkScannedCode(raw: string, pattern?: RegExp): ScannedCodeCheck {
  const code = normalizeScannedCode(raw)
  if (!code) return { valid: false, code, reason: 'empty' }
  if (pattern && !pattern.test(code)) return { valid: false, code, reason: 'pattern' }
  return { valid: true, code }
}

export interface LastRead {
  code: string
  at: number
}

/**
 * Indica si la lectura repite la anterior dentro de la ventana de espera.
 * Mientras el código sigue frente a la cámara, cada cuadro lo vuelve a
 * leer: quien llama renueva `at` en cada aparición, así el mismo código
 * se vuelve a aceptar recién cuando estuvo fuera de cuadro 2,5 s.
 */
export function isRepeatedRead(
  code: string,
  last: LastRead | null,
  now: number,
  windowMs = REPEATED_READ_WINDOW_MS,
): boolean {
  return Boolean(last && last.code === code && now - last.at < windowMs)
}
