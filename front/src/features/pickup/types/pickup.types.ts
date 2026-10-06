export interface ApiPickupBranch {
  id: number
  nombre: string
  provincia: string
  ciudad: string
  direccion: string
  latitud: number | null
  longitud: number | null
}

export interface ApiPickupValidation {
  paquete_id: string
  numero_paquete: string
  descripcion: string
  peso_kg: number
  estado_actual: string
  disponible_para_retiro: boolean
  motivo_no_disponible: string | null
  tipo_entrega: 'sucursal' | 'domicilio'
  sucursal_destino: ApiPickupBranch | null
  sucursal_actual: ApiPickupBranch | null
  datos_destinatario: { nombre: string; telefono: string; email: string }
  requisitos_retiro: { titular: string; tercero_autorizado: string }
}

export interface PickupValidationResponse {
  status: 'success'
  data: ApiPickupValidation
}

export interface PickupValidation {
  packageId: string
  packageNumber: string
  description: string
  weightKg: number
  status: string
  available: boolean
  unavailableReason: string | null
  deliveryType: 'sucursal' | 'domicilio'
  destinationBranch: ApiPickupBranch | null
  currentBranch: ApiPickupBranch | null
  recipient: { name: string; phone: string; email: string }
  requirements: { recipient: string; authorizedPerson: string }
}

export type PickupType = 'TITULAR' | 'TERCERO_AUTORIZADO'

export interface RegisterPickupInput {
  packageId: string
  type: PickupType
  documentType: string
  documentNumber: string
  recipientOver16: boolean
  authorizedName: string
  hasRecipientDocumentCopy: boolean
  hasSignedAuthorization: boolean
  notes: string
}

export interface ApiRegisteredPickup {
  paquete_id: string
  numero_paquete: string
  estado: string
  tipo_retiro: PickupType
  receptor_nombre: string
  receptor_documento: string
  es_autorizado: boolean
  usuario_administrativo_id: string
  usuario_administrativo_nombre: string
  fecha_hora_entrega: string
  sucursal_id: number | null
  observaciones: string | null
}

export interface RegisterPickupResponse {
  status: 'success'
  message: string
  data: ApiRegisteredPickup
}

export interface RegisteredPickup {
  packageNumber: string
  status: string
  recipientName: string
  recipientDocument: string
  operatorName: string
  deliveredAt: string
}
