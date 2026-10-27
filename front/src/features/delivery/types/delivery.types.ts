export interface DriverPosition { latitude: number; longitude: number; updatedAt: string }
export interface ApiDriverPosition { latitud: number; longitud: number; actualizado_at: string }
export interface DeliveryReceipt { eventId: string; packageId: string; result: string; receiverName: string | null; signatureAvailable: boolean; occurredAt: string }
export interface ApiDeliveryReceipt { evento_id: string; paquete_id: string; resultado: string; receptor_nombre: string | null; firma_disponible: boolean; fecha_hora: string }
export interface ReceiverInput { name: string; document: string; birthDate: string; authorized: boolean; signature: string }
export type DeliveryOperation =
  | { operationId: string; action: 'delivery'; receiver: ReceiverInput }
  | { operationId: string; action: 'failed'; reason: string }
export interface RecipientContact { name: string; phone: string | null }
