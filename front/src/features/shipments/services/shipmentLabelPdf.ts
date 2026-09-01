import JsBarcode from 'jsbarcode'
import type { CreatedShipment } from '../types/shipment.types'

function getDestination(shipment: CreatedShipment) {
  if (shipment.destinationBranch) {
    const branch = shipment.destinationBranch
    return `${branch.name} - ${branch.address}, ${branch.city}, ${branch.province}`
  }

  return [
    shipment.destinationAddress,
    shipment.destinationCity,
    shipment.destinationProvince,
  ]
    .filter(Boolean)
    .join(', ')
}

function createBarcodeDataUrl(value: string) {
  const canvas = document.createElement('canvas')
  JsBarcode(canvas, value, {
    format: 'CODE128',
    width: 3,
    height: 90,
    margin: 12,
    displayValue: true,
    fontSize: 20,
    textMargin: 8,
    background: '#ffffff',
    lineColor: '#000000',
  })
  return canvas.toDataURL('image/png')
}

export async function downloadShipmentLabelsPdf(shipment: CreatedShipment) {
  const { jsPDF } = await import('jspdf')
  const documentPdf = new jsPDF({ unit: 'mm', format: 'a4' })
  const destination = getDestination(shipment)
  const createdAt = new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(shipment.createdAt))

  shipment.packages.forEach((shipmentPackage, index) => {
    if (index > 0) documentPdf.addPage()

    documentPdf.setDrawColor(15, 23, 42)
    documentPdf.setLineWidth(0.6)
    documentPdf.rect(12, 12, 186, 170)

    documentPdf.setFillColor(79, 70, 229)
    documentPdf.roundedRect(18, 18, 16, 16, 2, 2, 'F')
    documentPdf.setTextColor(255, 255, 255)
    documentPdf.setFont('helvetica', 'bold')
    documentPdf.setFontSize(12)
    documentPdf.text('GE', 26, 28.5, { align: 'center' })

    documentPdf.setTextColor(15, 23, 42)
    documentPdf.setFontSize(15)
    documentPdf.text('Gestión de envíos', 39, 24)
    documentPdf.setFont('helvetica', 'normal')
    documentPdf.setFontSize(9)
    documentPdf.text('Etiqueta de admisión', 39, 30)

    documentPdf.setFont('helvetica', 'bold')
    documentPdf.setFontSize(9)
    documentPdf.text('BULTO', 187, 22, { align: 'right' })
    documentPdf.setFontSize(15)
    documentPdf.text(`${index + 1} / ${shipment.packages.length}`, 187, 30, {
      align: 'right',
    })

    documentPdf.line(18, 39, 192, 39)
    documentPdf.setFontSize(8)
    documentPdf.text('REMITENTE', 18, 46)
    documentPdf.text('DESTINATARIO', 108, 46)
    documentPdf.setFontSize(12)
    documentPdf.text(shipment.senderName, 18, 53)
    documentPdf.text(shipment.recipientName, 108, 53)
    documentPdf.setFont('helvetica', 'normal')
    documentPdf.setFontSize(9)
    documentPdf.text(`DNI ${shipment.senderDocument}`, 18, 59)
    documentPdf.text(shipment.senderPhone, 18, 65)
    documentPdf.text(shipment.recipientPhone, 108, 59)

    documentPdf.line(18, 71, 192, 71)
    documentPdf.setFont('helvetica', 'bold')
    documentPdf.setFontSize(8)
    documentPdf.text(
      shipment.deliveryType === 'sucursal'
        ? 'DESTINO - RETIRO EN SUCURSAL'
        : 'DESTINO - ENTREGA A DOMICILIO',
      18,
      78,
    )
    documentPdf.setFontSize(11)
    const destinationLines = documentPdf.splitTextToSize(destination, 170)
    documentPdf.text(destinationLines, 18, 85)

    const barcodeDataUrl = createBarcodeDataUrl(shipmentPackage.packageNumber)
    documentPdf.addImage(barcodeDataUrl, 'PNG', 35, 98, 140, 38)

    documentPdf.line(18, 141, 192, 141)
    documentPdf.setFontSize(8)
    documentPdf.text('CONTENIDO DECLARADO', 18, 148)
    documentPdf.text('PESO', 105, 148)
    documentPdf.text('MEDIDAS', 135, 148)
    documentPdf.setFontSize(10)
    documentPdf.text(shipmentPackage.description, 18, 155, { maxWidth: 80 })
    documentPdf.text(`${shipmentPackage.weightKg} kg`, 105, 155)
    documentPdf.text(
      `${shipmentPackage.lengthCm} x ${shipmentPackage.widthCm} x ${shipmentPackage.heightCm} cm`,
      135,
      155,
    )

    documentPdf.line(18, 164, 192, 164)
    documentPdf.setFont('helvetica', 'normal')
    documentPdf.setFontSize(8)
    documentPdf.text(`Seguimiento: ${shipment.trackingToken}`, 18, 172)
    documentPdf.text(`Registrado: ${createdAt}`, 192, 172, { align: 'right' })
  })

  documentPdf.save(`etiquetas-${shipment.trackingToken}.pdf`)
}
