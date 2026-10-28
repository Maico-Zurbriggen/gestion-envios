/**
 * Arma el HTML de las etiquetas de paquetes para la impresora configurada.
 * Módulo puro: recibe el código de barras ya dibujado como SVG, así se
 * prueba desde `tests/` con Node.
 */
import { escapeHtml } from './printHtml.ts'
import type { LabelLayout } from './printerProfiles.ts'

export interface ShipmentLabelData {
  packageNumber: string
  trackingToken: string
  recipientName: string
  destination: string
  deliveryType?: 'domicilio' | 'sucursal' | null
  weightKg?: number | null
  /** Medidas ya formateadas, por ejemplo `30 × 20 × 10 cm`. */
  dimensions?: string | null
  /** Posición del paquete dentro del envío, desde 1. */
  index?: number | null
  total?: number | null
  /** Fecha ya formateada para mostrar. */
  date?: string | null
  /** Rótulo de la fecha: `Registrado`, `Reimpreso`, etc. */
  dateCaption?: string
}

/** Dibuja el Code 128 del valor y devuelve el SVG como texto. */
export type BarcodeRenderer = (value: string) => string

export function formatDimensions(lengthCm: number, widthCm: number, heightCm: number): string {
  return `${lengthCm} × ${widthCm} × ${heightCm} cm`
}

/** `1/3` en la etiqueta chica, `Paquete 1 de 3` en la completa; vacío si no se conoce. */
export function getPieceText(label: Pick<ShipmentLabelData, 'index' | 'total'>, variant: LabelLayout['variant']): string {
  if (!label.index || !label.total) return ''
  return variant === 'compact' ? `${label.index}/${label.total}` : `Paquete ${label.index} de ${label.total}`
}

/** Repite cada etiqueta `copies` veces seguidas, para pegarlas sin mezclar paquetes. */
export function expandCopies<T>(labels: readonly T[], copies: number): T[] {
  const count = Math.max(1, Math.trunc(copies) || 1)
  return labels.flatMap((label) => Array.from({ length: count }, () => label))
}

function deliveryCaption(deliveryType: ShipmentLabelData['deliveryType']) {
  if (deliveryType === 'sucursal') return 'Destino · Retiro en sucursal'
  if (deliveryType === 'domicilio') return 'Destino · Entrega a domicilio'
  return 'Destino'
}

function weightAndDimensions(label: ShipmentLabelData) {
  const weight = label.weightKg != null ? `${label.weightKg} kg` : ''
  return [weight, label.dimensions ?? ''].filter(Boolean).join(' · ')
}

function detail(term: string, value: string, className = '') {
  if (!value) return ''
  return `<div${className ? ` class="${className}"` : ''}><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(value)}</dd></div>`
}

function compactLabel(label: ShipmentLabelData, barcode: string) {
  const piece = getPieceText(label, 'compact')
  return `<div class="label label--compact">` +
    `<div class="barcode">${barcode}</div>` +
    `<div class="meta"><strong class="code">${escapeHtml(label.packageNumber)}</strong>${piece ? `<span class="piece">${escapeHtml(piece)}</span>` : ''}</div>` +
    `</div>`
}

function fullLabel(label: ShipmentLabelData, barcode: string, layout: LabelLayout) {
  const piece = getPieceText(label, 'full')
  const date = label.date ? `${label.dateCaption ?? 'Fecha'}: ${label.date}` : ''
  return `<div class="label label--full label--${layout.orientation}">` +
    `<header class="head"><span class="brand">Gestión de Envíos</span>${piece ? `<span class="piece">${escapeHtml(piece)}</span>` : ''}</header>` +
    `<div class="body">` +
    `<div class="main">` +
    `<div class="code">${escapeHtml(label.packageNumber)}</div>` +
    `<div class="barcode">${barcode}</div>` +
    `<div class="token">Seguimiento <strong>${escapeHtml(label.trackingToken)}</strong></div>` +
    `</div>` +
    `<div class="info">` +
    `<dl class="details">` +
    detail('Destinatario', label.recipientName) +
    detail(deliveryCaption(label.deliveryType), label.destination, 'details__destination') +
    detail('Peso y medidas', weightAndDimensions(label)) +
    `</dl>` +
    (date ? `<footer class="foot">${escapeHtml(date)}</footer>` : '') +
    `</div>` +
    `</div>` +
    `</div>`
}

function mm(value: number) {
  return `${value}mm`
}

function buildStyles(layout: LabelLayout) {
  const isSheet = layout.labelWidthMm < layout.pageWidthMm
  const wideDetails = layout.variant === 'full' && layout.orientation === 'portrait' && layout.labelWidthMm >= 90
  return `
@page { size: ${mm(layout.pageWidthMm)} ${mm(layout.pageHeightMm)}; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; color: black; background: white; }
body { font-family: Arial, Helvetica, sans-serif; font-size: ${layout.fontSizePt}pt; line-height: 1.2; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: ${mm(layout.pageWidthMm)}; height: calc(${mm(layout.pageHeightMm)} - 0.3mm); overflow: hidden; break-after: page; page-break-after: always; ${isSheet ? `padding: 12mm ${mm((layout.pageWidthMm - layout.labelWidthMm) / 2)};` : ''} }
.page:last-child { break-after: auto; page-break-after: auto; }
.label { width: ${mm(layout.labelWidthMm)}; height: ${isSheet ? mm(layout.labelHeightMm) : '100%'}; padding: ${mm(layout.paddingMm)}; overflow: hidden; display: flex; flex-direction: column; ${isSheet ? 'border: 0.4mm solid black; border-radius: 2mm;' : ''} }
.barcode svg { display: block; width: 100%; height: 100%; }
.code { font-family: 'Courier New', Courier, monospace; font-weight: 700; letter-spacing: 0.02em; white-space: nowrap; overflow: hidden; }
.label--compact { gap: 0.6mm; padding-inline: 2mm; }
.label--compact .barcode { flex: 1 1 auto; min-height: 0; }
.label--compact .meta { display: flex; align-items: baseline; justify-content: space-between; gap: 1mm; }
.label--compact .piece { font-weight: 700; white-space: nowrap; }
.label--full { gap: 1.2mm; }
.head { display: flex; align-items: baseline; justify-content: space-between; gap: 2mm; padding-bottom: 0.8mm; border-bottom: 0.3mm solid black; }
.brand { font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.head .piece { font-weight: 700; white-space: nowrap; }
.body { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 1.5mm; }
.main { display: flex; flex-direction: column; gap: 0.8mm; }
.label--full .code { font-size: ${layout.orientation === 'landscape' ? '1.6em' : '2em'}; line-height: 1.1; }
.label--full .barcode { height: ${mm(layout.barcodeHeightMm)}; }
.token { font-size: 0.9em; }
.token strong { font-family: 'Courier New', Courier, monospace; }
.info { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 1mm; overflow: hidden; }
.details { display: grid; ${wideDetails ? 'grid-template-columns: 1fr 1fr;' : ''} gap: 0.8mm 3mm; margin: 0; }
.details div { min-width: 0; }
${wideDetails ? '.details__destination { grid-column: 1 / -1; }' : ''}
.details dt { font-size: 0.75em; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.details dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; }
.foot { margin-top: auto; font-size: 0.85em; }
.label--landscape .body { flex-direction: row; gap: 3mm; }
.label--landscape .main { flex: 0 0 55%; min-width: 0; }
.label--landscape .info { flex: 1 1 auto; min-width: 0; }
`
}

/** Documento HTML completo, una etiqueta por página, listo para `printHtml`. */
export function buildShipmentLabelsHtml(
  labels: readonly ShipmentLabelData[],
  layout: LabelLayout,
  copies: number,
  renderBarcode: BarcodeRenderer,
): string {
  const barcodes = new Map<string, string>()
  const pages = expandCopies(labels, copies).map((label) => {
    let barcode = barcodes.get(label.packageNumber)
    if (barcode === undefined) {
      barcode = renderBarcode(label.packageNumber)
      barcodes.set(label.packageNumber, barcode)
    }
    const content = layout.variant === 'compact' ? compactLabel(label, barcode) : fullLabel(label, barcode, layout)
    return `<section class="page">${content}</section>`
  })
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Etiquetas de envío</title><style>${buildStyles(layout)}</style></head><body>${pages.join('')}</body></html>`
}
