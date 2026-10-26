import type {
  ApiClaim, Claim, ClaimContext, ClaimContextResponse, ClaimErrorResponse,
  ClaimFieldErrors, ClaimFormValues, CreateClaimRequest, CreateClaimResponse,
} from '../types/claim.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
const fieldNames: Record<string, keyof ClaimFieldErrors> = {
  tipo: 'type', numero_paquete: 'packageNumber', descripcion: 'description',
  contacto_nombre: 'contactName', contacto_email: 'contactEmail',
  contacto_telefono: 'contactPhone', contacto: 'contact',
}

export class ClaimsApiError extends Error {
  readonly status?: number
  readonly fieldErrors: ClaimFieldErrors

  constructor(message: string, status?: number, fieldErrors: ClaimFieldErrors = {}) {
    super(message)
    this.name = 'ClaimsApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

function mapClaim(data: ApiClaim): Claim {
  return {
    id: data.id, packageNumber: data.numero_paquete, type: data.tipo,
    status: data.estado, description: data.descripcion, resolution: data.resolucion,
    createdAt: data.fecha_creacion, updatedAt: data.ultima_actualizacion,
  }
}

async function request(token: string, init?: RequestInit, signal?: AbortSignal): Promise<unknown> {
  if (!apiUrl) throw new ClaimsApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}/reclamos/seguimiento/${encodeURIComponent(token)}`, {
      ...init, signal, headers: { Accept: 'application/json', ...init?.headers },
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ClaimsApiError('No pudimos conectarnos. Revisá tu conexión e intentá nuevamente.')
  }
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const fieldErrors: ClaimFieldErrors = {}
    const error = payload as ClaimErrorResponse | null
    let message = 'No pudimos completar la operación. Intentá nuevamente.'
    if (response.status >= 500) message = 'El servicio no está disponible. Intentá nuevamente más tarde.'
    else if (response.status === 404) message = 'No encontramos el envío. Volvé a consultar tu código de seguimiento.'
    else if (response.status === 409) message = 'Ya hay un reclamo de este tipo en curso para ese envío o paquete. Revisá los reclamos anteriores.'
    else if (response.status === 400 || response.status === 422) {
      message = error?.message || 'Revisá los datos del reclamo e intentá nuevamente.'
      for (const issue of error?.errors ?? []) {
        const field = fieldNames[issue.field ?? '']
        if (field && issue.message) fieldErrors[field] = issue.message
      }
    }
    throw new ClaimsApiError(message, response.status, fieldErrors)
  }
  return payload
}

export async function getClaimContext(token: string, signal?: AbortSignal): Promise<ClaimContext> {
  const response = await request(token, undefined, signal) as ClaimContextResponse
  const data = response?.data
  if (response?.status !== 'success' || !data?.token_seguimiento ||
    typeof data.puede_iniciar !== 'boolean' || !Array.isArray(data.tipos_reclamo) ||
    !Array.isArray(data.paquetes) || !Array.isArray(data.reclamos)) {
    throw new ClaimsApiError('No pudimos cargar los datos del reclamo. Intentá nuevamente.')
  }
  return {
    trackingToken: data.token_seguimiento, canCreate: data.puede_iniciar,
    unavailableReason: data.motivo_no_habilitado, maxActiveClaims: data.max_reclamos_activos,
    types: data.tipos_reclamo.map((type) => ({ code: type.codigo, description: type.descripcion })),
    packages: data.paquetes.map((item) => ({
      packageNumber: item.numero_paquete, description: item.descripcion, status: item.estado,
    })),
    claims: data.reclamos.map(mapClaim),
  }
}

export async function createClaim(token: string, input: ClaimFormValues): Promise<Claim> {
  if (!input.type) throw new ClaimsApiError('Elegí el motivo del reclamo.')
  const body: CreateClaimRequest = {
    tipo: input.type, descripcion: input.description.trim(),
    numero_paquete: input.packageNumber || null, contacto_nombre: input.contactName.trim(),
    contacto_email: input.contactEmail.trim() || null, contacto_telefono: input.contactPhone.trim() || null,
  }
  const response = await request(token, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }) as CreateClaimResponse
  if (response?.status !== 'success' || !response.data?.id) {
    throw new ClaimsApiError('No pudimos confirmar el registro. Actualizá los reclamos antes de volver a enviar.')
  }
  return mapClaim(response.data)
}
