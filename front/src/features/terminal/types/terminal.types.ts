export interface ApiScannedPackage {
  paquete_id: string
  numero_paquete: string
  descripcion: string
  peso_kg: number
  largo_cm: number
  ancho_cm: number
  alto_cm: number
  observaciones: string | null
  estado_actual: string
  disponible_para_recepcion: boolean
  motivo_no_disponible: string | null
  envio: {
    token_seguimiento: string
    remitente_nombre: string
    remitente_documento: string
    destinatario_nombre: string
    destino: string
    tipo_entrega?: string
  }
  bulto?: number
  total_bultos?: number
}

export interface ScannedPackage {
  id: string
  code: string
  description: string
  weightKg: number
  dimensions: string
  notes: string | null
  status: string
  available: boolean
  unavailableReason: string | null
  trackingToken: string
  senderName: string
  senderDocument: string
  recipientName: string
  destination: string
  deliveryType: 'domicilio' | 'sucursal' | null
  /** Posición del paquete en el envío, para la etiqueta «1 de 3». */
  packageIndex: number
  packageTotal: number
}

export interface ReceptionInput { code: string; branchId: number; notes: string; scaleWeightKg: number | null }
export interface Reception {
  code: string
  status: string
  branchName: string
  receivedAt: string
  trackingToken: string
  scaleWeightKg: number | null
  /** Aviso si la balanza difiere más de un 10 % del peso declarado. */
  weightWarning: string | null
  /** Si queda para retirar en esta sucursal, hasta cuándo. */
  pickupUntil: string | null
}
