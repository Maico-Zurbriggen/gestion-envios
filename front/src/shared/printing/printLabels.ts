import JsBarcode from 'jsbarcode'
import { printHtml } from './printHtml'
import { getLabelLayout, resolveLabelSize, type PrintSettings } from './printerProfiles'
import { buildShipmentLabelsHtml, type ShipmentLabelData } from './shipmentLabels'

const SVG_NS = 'http://www.w3.org/2000/svg'

/**
 * Code 128 en SVG, plano y sin márgenes ni texto: el número se imprime
 * aparte. Sin ancho ni alto fijos, el SVG ocupa el lugar que le da la etiqueta.
 */
function renderBarcodeSvg(value: string): string {
  const svg = document.createElementNS(SVG_NS, 'svg')
  JsBarcode(svg, value, {
    format: 'CODE128',
    flat: true,
    margin: 0,
    width: 2,
    height: 100,
    displayValue: false,
    background: 'white',
    lineColor: 'black',
  })
  svg.removeAttribute('width')
  svg.removeAttribute('height')
  svg.setAttribute('preserveAspectRatio', 'none')
  svg.setAttribute('shape-rendering', 'crispEdges')
  svg.setAttribute('aria-hidden', 'true')
  return svg.outerHTML
}

/** Imprime las etiquetas con la impresora, el tamaño y las copias configurados. */
export function printShipmentLabels(labels: readonly ShipmentLabelData[], settings: PrintSettings) {
  if (labels.length === 0) return
  const layout = getLabelLayout(resolveLabelSize(settings))
  printHtml(buildShipmentLabelsHtml(labels, layout, settings.copies, renderBarcodeSvg))
}

/** Datos ficticios para la impresión de prueba. */
export const SAMPLE_LABEL: ShipmentLabelData = {
  packageNumber: 'PAQ-PRUEBA0001',
  trackingToken: 'ENV-PRUEBA0001',
  recipientName: 'Destinatario de prueba',
  destination: 'Av. Siempre Viva 742, Rafaela, Santa Fe',
  deliveryType: 'domicilio',
  weightKg: 1.5,
  dimensions: '30 × 20 × 10 cm',
  index: 1,
  total: 1,
  dateCaption: 'Prueba',
}
