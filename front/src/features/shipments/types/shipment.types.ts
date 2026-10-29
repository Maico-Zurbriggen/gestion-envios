export type DeliveryType = 'domicilio' | 'sucursal'

export interface ShipmentPackageInput {
  description: string
  weightKg: number
  lengthCm: number
  widthCm: number
  heightCm: number
  notes: string | null
}

export interface CreateShipmentInput {
  senderName: string
  senderDocument: string
  senderPhone: string
  senderEmail: string
  recipientName: string
  recipientPhone: string
  recipientEmail: string
  deliveryType: DeliveryType
  destinationProvince: string | null
  destinationCity: string | null
  destinationAddress: string | null
  destinationLatitude: number | null
  destinationLongitude: number | null
  destinationBranchId: number | null
  /** Sucursal donde el remitente va a llevar los paquetes. */
  originBranchId: number
  termsAccepted: boolean
  packages: ShipmentPackageInput[]
}

export interface ApiBranch {
  id: number
  nombre: string
  provincia: string
  ciudad: string
  direccion: string
  latitud: number | null
  longitud: number | null
}

export interface Branch {
  id: number
  name: string
  province: string
  city: string
  address: string
  latitude: number | null
  longitude: number | null
}

export interface BranchesSuccessResponse {
  status: 'success'
  data: ApiBranch[]
}

export interface ApiCreatedPackage {
  id: string
  numero_paquete: string
  descripcion: string
  peso_kg: number
  largo_cm: number
  ancho_cm: number
  alto_cm: number
  observaciones: string | null
  estado: string
}

export interface ApiCreatedShipment {
  id: string
  token_seguimiento: string
  remitente_nombre: string
  remitente_documento: string
  remitente_telefono: string
  remitente_email: string
  destinatario_nombre: string
  destinatario_telefono: string
  destinatario_email: string
  tipo_entrega: DeliveryType
  provincia_destino: string | null
  ciudad_destino: string | null
  direccion_destino: string | null
  latitud_destino: number | null
  longitud_destino: number | null
  sucursal_destino: ApiBranch | null
  sucursal_origen?: ApiBranch | null
  paquetes: ApiCreatedPackage[]
  created_at: string
  admitir_hasta?: string | null
}

export interface CreateShipmentSuccessResponse {
  status: 'success'
  message: string
  data: ApiCreatedShipment
}

export interface CreatedPackage {
  id: string
  packageNumber: string
  description: string
  weightKg: number
  lengthCm: number
  widthCm: number
  heightCm: number
  notes: string | null
  status: string
}

export interface CreatedShipment {
  id: string
  trackingToken: string
  senderName: string
  senderDocument: string
  senderPhone: string
  senderEmail: string
  recipientName: string
  recipientPhone: string
  recipientEmail: string
  deliveryType: DeliveryType
  destinationProvince: string | null
  destinationCity: string | null
  destinationAddress: string | null
  destinationLatitude: number | null
  destinationLongitude: number | null
  destinationBranch: Branch | null
  /** Dónde tiene que llevar los paquetes el remitente. */
  originBranch: Branch | null
  packages: CreatedPackage[]
  createdAt: string
  /** Último día para llevarlo a una sucursal; después el registro vence. */
  admitBy: string | null
}
