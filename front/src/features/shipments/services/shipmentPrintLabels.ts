import { formatDimensions, type ShipmentLabelData } from '../../../shared/printing/shipmentLabels'
import type { CreatedShipment } from '../types/shipment.types'

/** Una etiqueta por paquete del envío recién registrado. */
export function getShipmentPrintLabels(shipment: CreatedShipment, destination: string, createdAt: string): ShipmentLabelData[] {
  return shipment.packages.map((shipmentPackage, index) => ({
    packageNumber: shipmentPackage.packageNumber,
    trackingToken: shipment.trackingToken,
    recipientName: shipment.recipientName,
    destination,
    deliveryType: shipment.deliveryType,
    weightKg: shipmentPackage.weightKg,
    dimensions: formatDimensions(shipmentPackage.lengthCm, shipmentPackage.widthCm, shipmentPackage.heightCm),
    index: index + 1,
    total: shipment.packages.length,
    date: createdAt,
    dateCaption: 'Registrado',
  }))
}
