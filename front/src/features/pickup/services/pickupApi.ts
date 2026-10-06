import type {
  PickupValidation,
  PickupValidationResponse,
  RegisteredPickup,
  RegisterPickupInput,
  RegisterPickupResponse,
} from '../types/pickup.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

interface ApiErrorResponse {
  code?: string
  message?: string
  errors?: Array<{ field?: string; message?: string }>
  detail?: string | Array<{ msg?: string }>
}

export class PickupApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PickupApiError'
  }
}

function errorMessage(payload: unknown, status: number) {
  if (status === 401) return 'Tu sesión venció. Iniciá sesión nuevamente.'
  if (status === 403) return 'Tu cuenta no tiene permiso para registrar retiros.'
  if (status === 404) return 'No encontramos un paquete con ese código.'
  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'
  const error = payload as ApiErrorResponse | null
  if (error && (status === 400 || status === 409 || status === 422)) {
    const messages = error.errors?.map((item) => item.message).filter((item): item is string => Boolean(item))
    if (messages?.length) return messages.join(' ')
    if (Array.isArray(error.detail)) {
      const details = error.detail.map((item) => item.msg).filter((item): item is string => Boolean(item))
      if (details.length) return details.join(' ')
    }
    if (error.message) return error.message
  }
  return 'No pudimos completar la operación. Revisá los datos e intentá nuevamente.'
}

async function request(path: string, token: string, init?: RequestInit): Promise<unknown> {
  if (!apiUrl) throw new PickupApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...init?.headers },
    })
  } catch {
    throw new PickupApiError('No pudimos conectarnos con el servidor. Intentá nuevamente.')
  }
  let payload: unknown
  try { payload = await response.json() } catch { payload = null }
  if (!response.ok) throw new PickupApiError(errorMessage(payload, response.status))
  return payload
}

export async function validatePickup(code: string, token: string): Promise<PickupValidation> {
  const response = await request(`/sucursal/paquetes/${encodeURIComponent(code)}/validar-retiro`, token) as PickupValidationResponse
  if (response?.status !== 'success' || !response.data?.paquete_id || !response.data?.numero_paquete) {
    throw new PickupApiError('El servidor devolvió una respuesta inesperada.')
  }
  const data = response.data
  return {
    packageId: data.paquete_id,
    packageNumber: data.numero_paquete,
    description: data.descripcion,
    weightKg: data.peso_kg,
    status: data.estado_actual,
    available: data.disponible_para_retiro,
    unavailableReason: data.motivo_no_disponible,
    deliveryType: data.tipo_entrega,
    destinationBranch: data.sucursal_destino,
    currentBranch: data.sucursal_actual,
    recipient: { name: data.datos_destinatario.nombre, phone: data.datos_destinatario.telefono, email: data.datos_destinatario.email },
    requirements: { recipient: data.requisitos_retiro.titular, authorizedPerson: data.requisitos_retiro.tercero_autorizado },
  }
}

export async function registerPickup(input: RegisterPickupInput, token: string): Promise<RegisteredPickup> {
  const response = await request(`/sucursal/paquetes/${encodeURIComponent(input.packageId)}/registrar-retiro`, token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tipo_retiro: input.type,
      documento_presentado: { tipo: input.documentType, numero: input.documentNumber },
      destinatario_mayor_16: input.recipientOver16,
      tercero_autorizado: input.type === 'TERCERO_AUTORIZADO' ? {
        nombre_completo: input.authorizedName,
        documento: input.documentNumber,
        posee_copia_dni_titular: input.hasRecipientDocumentCopy,
        posee_nota_autorizacion: input.hasSignedAuthorization,
      } : null,
      observaciones: input.notes.trim() || null,
    }),
  }) as RegisterPickupResponse
  if (response?.status !== 'success' || !response.data?.numero_paquete || !response.data?.fecha_hora_entrega) {
    throw new PickupApiError('El servidor devolvió una respuesta inesperada.')
  }
  return {
    packageNumber: response.data.numero_paquete,
    status: response.data.estado,
    recipientName: response.data.receptor_nombre,
    recipientDocument: response.data.receptor_documento,
    operatorName: response.data.usuario_administrativo_nombre,
    deliveredAt: response.data.fecha_hora_entrega,
  }
}
