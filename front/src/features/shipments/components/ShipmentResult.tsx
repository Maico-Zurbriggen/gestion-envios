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
import { getShipmentPrintLabels } from '../services/shipmentPrintLabels'
import { useAppSelector } from '../../../app/store'
import { PrintLabelsButton } from '../../../shared/printing/PrintLabelsButton'
import { selectCurrentUser } from '../../auth/redux/authSlice'
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
  // Las etiquetas térmicas se imprimen en el mostrador; el cliente solo necesita el comprobante.
  const user = useAppSelector(selectCurrentUser)
  const isCounterStaff = Boolean(user?.role && ['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN'].includes(user.role))
  const admitBy = shipment.admitBy
    ? new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(shipment.admitBy))
    : null
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
        <h1>Tu envío está registrado</h1>
        <p>
          Guardá el código de seguimiento: con él seguís el envío y te avisamos
          por correo y WhatsApp cada novedad.
        </p>
        <ol className="shipment-next-steps">
          <li>
            <strong>Llevá cada paquete a {shipment.originBranch ? `${shipment.originBranch.name} (${shipment.originBranch.address}, ${shipment.originBranch.city})` : 'la sucursal elegida'}{admitBy ? ` antes del ${admitBy}` : ''}.</strong>
            <span>Si no lo llevás a tiempo, el registro vence y hay que hacerlo de nuevo.</span>
          </li>
          <li>
            <strong>Mostrá este comprobante, impreso o en el celular.</strong>
            <span>Escaneamos el código, pesamos el paquete y le pegamos la etiqueta de envío.</span>
          </li>
          <li>
            <strong>Listo: te avisamos cuando llegue a destino.</strong>
            <span>También le avisamos a quien lo recibe.</span>
          </li>
        </ol>

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
            Imprimir comprobante
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
          {isCounterStaff ? (
            <PrintLabelsButton
              labels={getShipmentPrintLabels(shipment, destination, createdAt)}
              className="shipment-secondary-action"
              label="Imprimir etiquetas (mostrador)"
            />
          ) : null}
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
                  <small>Comprobante para la sucursal</small>
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
