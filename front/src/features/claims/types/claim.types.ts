export type ClaimType = 'DEMORA' | 'DANIO' | 'EXTRAVIO' | 'OTRO'
export type ClaimStatus = 'ABIERTO' | 'EN_REVISION' | 'RESUELTO' | 'RECHAZADO'

export interface ApiClaim {
  id: string
  numero_paquete: string | null
  tipo: ClaimType
  estado: ClaimStatus
  descripcion: string
  resolucion: string | null
  fecha_creacion: string
  ultima_actualizacion: string
}

export interface ClaimContextResponse {
  status: 'success'
  data: {
    token_seguimiento: string
    puede_iniciar: boolean
    motivo_no_habilitado: string | null
    max_reclamos_activos: number
    tipos_reclamo: Array<{ codigo: ClaimType; descripcion: string }>
    paquetes: Array<{ numero_paquete: string; descripcion: string; estado: string }>
    reclamos: ApiClaim[]
  }
}

export interface CreateClaimRequest {
  tipo: ClaimType
  descripcion: string
  numero_paquete: string | null
  contacto_nombre: string
  contacto_email: string | null
  contacto_telefono: string | null
}

export interface CreateClaimResponse {
  status: 'success'
  message: string
  data: ApiClaim
}

export interface ClaimErrorResponse {
  code?: string
  message?: string
  errors?: Array<{ field?: string; message?: string }>
}

export interface Claim {
  id: string
  packageNumber: string | null
  type: ClaimType
  status: ClaimStatus
  description: string
  resolution: string | null
  createdAt: string
  updatedAt: string
}

export interface ClaimContext {
  trackingToken: string
  canCreate: boolean
  unavailableReason: string | null
  maxActiveClaims: number
  types: Array<{ code: ClaimType; description: string }>
  packages: Array<{ packageNumber: string; description: string; status: string }>
  claims: Claim[]
}

export interface ClaimFormValues {
  type: ClaimType | ''
  packageNumber: string
  description: string
  contactName: string
  contactEmail: string
  contactPhone: string
}

export type ClaimFieldErrors = Partial<Record<keyof ClaimFormValues | 'contact', string>>
