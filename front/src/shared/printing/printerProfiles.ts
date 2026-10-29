/**
 * Perfiles de impresora y tamaños de etiqueta (portados de Soderia-ERP).
 *
 * La impresora física se elige en el diálogo del navegador: el perfil solo
 * define el tamaño de la página (`@page`) y el diseño de la etiqueta. El
 * tamaño de papel tiene que coincidir con el configurado en el driver.
 * Módulo puro: se prueba desde `tests/` con Node.
 */

interface LabelSize {
  id: string
  name: string
  /** Ancho de la página, en milímetros. */
  widthMm: number
  /** Alto de la página, en milímetros. */
  heightMm: number
}

interface PrinterProfile {
  id: string
  name: string
  sizes: LabelSize[]
}

export const PRINTER_PROFILES: readonly PrinterProfile[] = [
  {
    id: 'zebra_zd220',
    name: 'Zebra ZD220 / Térmica genérica',
    sizes: [
      { id: '50x25', name: '50 mm × 25 mm', widthMm: 50, heightMm: 25 },
      { id: '40x30', name: '40 mm × 30 mm', widthMm: 40, heightMm: 30 },
    ],
  },
  {
    id: 'sato',
    name: 'SATO (CG408 / WS4 / Industrial)',
    sizes: [
      { id: '50x25', name: '50 mm × 25 mm', widthMm: 50, heightMm: 25 },
      { id: '40x30', name: '40 mm × 30 mm', widthMm: 40, heightMm: 30 },
      { id: '50x100', name: '50 mm × 100 mm', widthMm: 50, heightMm: 100 },
      { id: '100x50', name: '100 mm × 50 mm', widthMm: 100, heightMm: 50 },
    ],
  },
  {
    id: 'brother_ql800',
    name: 'Brother QL-800',
    sizes: [
      { id: '62x29', name: '62 mm × 29 mm (DK-11209)', widthMm: 62, heightMm: 29 },
      // Rotada: la etiqueta de 29 × 90 mm se imprime apaisada.
      { id: '29x90', name: '29 mm × 90 mm (DK-11201)', widthMm: 90, heightMm: 29 },
    ],
  },
  {
    id: 'shipping_4x6',
    name: 'Etiqueta de envío 100x150 (4x6")',
    sizes: [{ id: '100x150', name: '100 mm × 150 mm (4" × 6")', widthMm: 100, heightMm: 150 }],
  },
  {
    id: 'a4',
    name: 'Hoja A4 (impresora común)',
    sizes: [{ id: 'a4', name: 'A4 · 210 mm × 297 mm', widthMm: 210, heightMm: 297 }],
  },
]

export const MIN_COPIES = 1
export const MAX_COPIES = 10

export interface PrintSettings {
  profileId: string
  sizeId: string
  copies: number
}

export const DEFAULT_PRINT_SETTINGS: PrintSettings = { profileId: 'a4', sizeId: 'a4', copies: 1 }

export function findPrinterProfile(profileId: string): PrinterProfile {
  return PRINTER_PROFILES.find((profile) => profile.id === profileId) ?? findPrinterProfile(DEFAULT_PRINT_SETTINGS.profileId)
}

export function findLabelSize(profile: PrinterProfile, sizeId: string): LabelSize {
  return profile.sizes.find((size) => size.id === sizeId) ?? profile.sizes[0]
}

export function clampCopies(value: unknown): number {
  const parsed = typeof value === 'number' ? value : Number.parseInt(String(value ?? ''), 10)
  if (!Number.isFinite(parsed)) return MIN_COPIES
  return Math.min(Math.max(Math.trunc(parsed), MIN_COPIES), MAX_COPIES)
}

/**
 * Convierte lo guardado (o lo elegido en el formulario) en una configuración
 * válida: perfil conocido, tamaño de ese perfil y copias entre 1 y 10.
 */
export function normalizePrintSettings(value: unknown): PrintSettings {
  const raw = (value && typeof value === 'object' ? value : {}) as Partial<Record<keyof PrintSettings, unknown>>
  const profile = findPrinterProfile(typeof raw.profileId === 'string' ? raw.profileId : '')
  const size = findLabelSize(profile, typeof raw.sizeId === 'string' ? raw.sizeId : '')
  return { profileId: profile.id, sizeId: size.id, copies: clampCopies(raw.copies ?? MIN_COPIES) }
}

export function resolveLabelSize(settings: PrintSettings): LabelSize {
  return findLabelSize(findPrinterProfile(settings.profileId), settings.sizeId)
}

export type LabelVariant = 'compact' | 'full'

export interface LabelLayout {
  /** `compact`: código de barras, número y n/m. `full`: etiqueta de envío completa. */
  variant: LabelVariant
  /** Disposición de la etiqueta completa: en columna o en dos columnas (apaisada). */
  orientation: 'portrait' | 'landscape'
  pageWidthMm: number
  pageHeightMm: number
  /** Área de la etiqueta dentro de la página (en A4 no ocupa la hoja entera). */
  labelWidthMm: number
  labelHeightMm: number
  paddingMm: number
  /** Cuerpo de texto, en puntos. */
  fontSizePt: number
  /** Alto del código de barras de la etiqueta completa, en milímetros. */
  barcodeHeightMm: number
}

/** Por debajo de este lado menor no entra la etiqueta completa. */
const FULL_LABEL_MIN_SIDE_MM = 45

function round(value: number, decimals = 1) {
  const factor = 10 ** decimals
  return Math.round(value * factor) / factor
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

/** Elige el diseño de la etiqueta según el tamaño del papel. */
export function getLabelLayout(size: LabelSize): LabelLayout {
  const pageWidthMm = size.widthMm
  const pageHeightMm = size.heightMm
  const variant: LabelVariant = Math.min(pageWidthMm, pageHeightMm) >= FULL_LABEL_MIN_SIDE_MM ? 'full' : 'compact'
  // En una hoja común se imprime una etiqueta grande por página, arriba, como el PDF.
  const isSheet = pageWidthMm >= 200 && pageHeightMm >= 280
  const labelWidthMm = isSheet ? pageWidthMm - 24 : pageWidthMm
  const labelHeightMm = isSheet ? 160 : pageHeightMm
  const orientation = labelWidthMm > labelHeightMm * 1.4 ? 'landscape' : 'portrait'

  if (variant === 'compact') {
    return {
      variant,
      orientation: 'landscape',
      pageWidthMm,
      pageHeightMm,
      labelWidthMm,
      labelHeightMm,
      // El margen lateral funciona como zona de silencio del Code 128.
      paddingMm: 1.5,
      fontSizePt: round(clamp(labelHeightMm / 3.6, 6, 9)),
      barcodeHeightMm: round(labelHeightMm * 0.55),
    }
  }

  const fontSizePt = round(clamp(Math.min(labelWidthMm, labelHeightMm * 0.75) / 9, 6.5, 13))
  return {
    variant,
    orientation,
    pageWidthMm,
    pageHeightMm,
    labelWidthMm,
    labelHeightMm,
    paddingMm: round(clamp(labelWidthMm * 0.04, 2.5, 8)),
    fontSizePt,
    barcodeHeightMm: round(clamp(labelHeightMm * (orientation === 'landscape' ? 0.3 : 0.26), 10, 42)),
  }
}
