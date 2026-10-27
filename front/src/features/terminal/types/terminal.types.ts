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
  }
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
}

export interface ReceptionInput { code: string; branchId: number; notes: string }
export interface Reception { code: string; status: string; branchName: string; receivedAt: string }
