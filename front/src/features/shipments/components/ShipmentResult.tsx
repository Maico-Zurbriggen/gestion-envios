import { useState } from 'react'
import {
  Check,
  CheckCircle2,
  Clipboard,
  Download,
  LoaderCircle,
  PackagePlus,
  Printer,
} from 'lucide-react'
import type { CreatedShipment } from '../types/shipment.types'
import { downloadShipmentLabelsPdf } from '../services/shipmentLabelPdf'
import { PackageBarcode } from './PackageBarcode'

interface ShipmentResultProps {
  shipment: CreatedShipment
  onCreateAnother: () => void
}

function getDestination(shipment: CreatedShipment) {
  if (shipment.destinationBranch) {
    const branch = shipment.destinationBranch
    return `${branch.name} — ${branch.address}, ${branch.city}, ${branch.province}`
  }

  return [
    shipment.destinationAddress,
    shipment.destinationCity,
    shipment.destinationProvince,
  ]
    .filter(Boolean)
    .join(', ')
}

export function ShipmentResult({
  shipment,
  onCreateAnother,
}: ShipmentResultProps) {
  const [tokenCopied, setTokenCopied] = useState(false)
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const destination = getDestination(shipment)
  const createdAt = new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(shipment.createdAt))

  async function copyTrackingToken() {
    try {
      await navigator.clipboard.writeText(shipment.trackingToken)
      setTokenCopied(true)
    } catch {
      setTokenCopied(false)
    }
  }

  async function downloadPdf() {
    setIsDownloadingPdf(true)
    setDownloadError(null)

    try {
      await downloadShipmentLabelsPdf(shipment)
    } catch {
      setDownloadError(
        'No pudimos generar el PDF. Podés imprimir la planilla mientras tanto.',
      )
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  return (
    <main className="shipment-result">
      <section className="shipment-result__summary shipment-screen-only">
        <span className="shipment-result__success-icon" aria-hidden="true">
          <CheckCircle2 size={32} />
        </span>
        <span className="eyebrow">Envío registrado</span>
        <h1>La planilla está lista</h1>
        <p>
          Imprimí una etiqueta por paquete, pegala en el bulto correspondiente y
          llevalo a la sucursal para que puedan escanearlo.
        </p>

        <div className="tracking-token">
          <span>Código de seguimiento</span>
          <strong>{shipment.trackingToken}</strong>
          <button type="button" onClick={copyTrackingToken}>
            {tokenCopied ? (
              <Check size={18} aria-hidden="true" />
            ) : (
              <Clipboard size={18} aria-hidden="true" />
            )}
            {tokenCopied ? 'Copiado' : 'Copiar'}
          </button>
        </div>

        <div className="shipment-result__actions">
          <button
            className="shipment-primary-action"
            type="button"
            onClick={() => window.print()}
          >
            <Printer size={19} aria-hidden="true" />
            Imprimir planilla
          </button>
          <button
            className="shipment-secondary-action"
            type="button"
            disabled={isDownloadingPdf}
            onClick={() => void downloadPdf()}
          >
            {isDownloadingPdf ? (
              <LoaderCircle className="loading-icon" size={19} aria-hidden="true" />
            ) : (
              <Download size={19} aria-hidden="true" />
            )}
            {isDownloadingPdf ? 'Generando PDF…' : 'Descargar PDF'}
          </button>
          <button
            className="shipment-secondary-action"
            type="button"
            onClick={onCreateAnother}
          >
            <PackagePlus size={19} aria-hidden="true" />
            Registrar otro envío
          </button>
        </div>
        {downloadError && (
          <p className="shipment-result__download-error" role="alert">
            {downloadError}
          </p>
        )}
      </section>

      <section
        className="shipping-labels"
        aria-label="Planilla de etiquetas del envío"
      >
        {shipment.packages.map((shipmentPackage, index) => (
          <article className="shipping-label" key={shipmentPackage.id}>
            <header className="shipping-label__header">
              <div className="shipping-label__brand">
                <span aria-hidden="true">GE</span>
                <div>
                  <strong>Gestión de envíos</strong>
                  <small>Etiqueta de admisión</small>
                </div>
              </div>
              <div className="shipping-label__piece">
                <span>Bulto</span>
                <strong>
                  {index + 1} / {shipment.packages.length}
                </strong>
              </div>
            </header>

            <div className="shipping-label__route">
              <div>
                <span>Remitente</span>
                <strong>{shipment.senderName}</strong>
                <small>DNI {shipment.senderDocument}</small>
                <small>{shipment.senderPhone}</small>
              </div>
              <div>
                <span>Destinatario</span>
                <strong>{shipment.recipientName}</strong>
                <small>{shipment.recipientPhone}</small>
              </div>
            </div>

            <div className="shipping-label__destination">
              <span>
                Destino ·{' '}
                {shipment.deliveryType === 'sucursal'
                  ? 'Retiro en sucursal'
                  : 'Entrega a domicilio'}
              </span>
              <strong>{destination}</strong>
            </div>

            <div className="shipping-label__barcode">
              <PackageBarcode value={shipmentPackage.packageNumber} />
            </div>

            <div className="shipping-label__details">
              <div>
                <span>Contenido declarado</span>
                <strong>{shipmentPackage.description}</strong>
              </div>
              <div>
                <span>Peso</span>
                <strong>{shipmentPackage.weightKg} kg</strong>
              </div>
              <div>
                <span>Medidas</span>
                <strong>
                  {shipmentPackage.lengthCm} × {shipmentPackage.widthCm} ×{' '}
                  {shipmentPackage.heightCm} cm
                </strong>
              </div>
            </div>

            <footer className="shipping-label__footer">
              <span>Seguimiento: {shipment.trackingToken}</span>
              <span>Registrado: {createdAt}</span>
            </footer>
          </article>
        ))}
      </section>
    </main>
  )
}
