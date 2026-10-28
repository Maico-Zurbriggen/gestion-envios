import { operationalRequest } from '../../../shared/services/operationalApi'

export type ClaimStatus = 'ABIERTO' | 'EN_REVISION' | 'RESUELTO' | 'RECHAZADO'
export type ClaimType = 'DEMORA' | 'DANIO' | 'EXTRAVIO' | 'OTRO'

interface ApiAdminClaim {
  id: string
  envio_id: string
  token_seguimiento: string
  remitente_nombre: string
  destinatario_nombre: string
  numero_paquete: string | null
  tipo: ClaimType
  descripcion: string
  contacto_nombre: string
  contacto_email: string | null
  contacto_telefono: string | null
  estado: ClaimStatus
  resolucion: string | null
  usuario_resolucion_nombre: string | null
  created_at: string
  updated_at: string
}

export interface AdminClaim {
  id: string
  trackingToken: string
  senderName: string
  recipientName: string
  packageCode: string | null
  type: ClaimType
  description: string
  contactName: string
  contactEmail: string | null
  contactPhone: string | null
  status: ClaimStatus
  resolution: string | null
  resolvedBy: string | null
  createdAt: string
  updatedAt: string
}

/** Transiciones que acepta el backend; cerrar exige una respuesta para el cliente. */
export const CLAIM_TRANSITIONS: Record<ClaimStatus, ClaimStatus[]> = {
  ABIERTO: ['EN_REVISION', 'RESUELTO', 'RECHAZADO'],
  EN_REVISION: ['RESUELTO', 'RECHAZADO'],
  RESUELTO: [],
  RECHAZADO: [],
}

function mapClaim(claim: ApiAdminClaim): AdminClaim {
  return {
    id: claim.id,
    trackingToken: claim.token_seguimiento,
    senderName: claim.remitente_nombre,
    recipientName: claim.destinatario_nombre,
    packageCode: claim.numero_paquete,
    type: claim.tipo,
    description: claim.descripcion,
    contactName: claim.contacto_nombre,
    contactEmail: claim.contacto_email,
    contactPhone: claim.contacto_telefono,
    status: claim.estado,
    resolution: claim.resolucion,
    resolvedBy: claim.usuario_resolucion_nombre,
    createdAt: claim.created_at,
    updatedAt: claim.updated_at,
  }
}

export async function listAdminClaims(token: string): Promise<AdminClaim[]> {
  const { data } = await operationalRequest<{ data: ApiAdminClaim[] }>('/admin/reclamos', token)
  return data.map(mapClaim)
}

export async function updateClaimStatus(id: string, status: ClaimStatus, resolution: string, token: string) {
  const payload = await operationalRequest<{ data: ApiAdminClaim; message: string | null }>(
    `/admin/reclamos/${id}/estado`,
    token,
    { method: 'PATCH', body: JSON.stringify({ estado: status, resolucion: resolution.trim() || null }) },
    { notFound: 'El reclamo ya no existe. Actualizá la bandeja.' },
  )
  return mapClaim(payload.data)
}
