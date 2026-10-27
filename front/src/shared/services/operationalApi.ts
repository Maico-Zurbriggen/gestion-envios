interface ApiErrorPayload {
  message?: string
  errors?: Array<{ field?: string; message?: string }>
}

export class OperationalApiError extends Error {
  readonly status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'OperationalApiError'
    this.status = status
  }
}

export async function operationalRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
  if (!apiUrl) throw new OperationalApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init, cache: 'no-store',
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch (error) {
    if (init?.signal?.aborted) throw error
    throw new OperationalApiError('No pudimos conectarnos. Revisá tu conexión y reintentá.')
  }
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    let message = 'No pudimos completar la operación. Actualizá los datos e intentá nuevamente.'
    if (response.status === 401) message = 'Tu sesión venció. Iniciá sesión nuevamente.'
    else if (response.status === 403) message = 'Tu cuenta no tiene permiso para realizar esta operación.'
    else if (response.status === 404) message = 'No encontramos el recurso solicitado o no está disponible para tu cuenta.'
    else if (response.status >= 500) message = 'El servicio no está disponible. Intentá nuevamente más tarde.'
    else if ([400, 409, 422].includes(response.status)) {
      const error = payload as ApiErrorPayload | null
      const issues = Array.isArray(error?.errors) ? error.errors.map((item) => item.message).filter(Boolean) : []
      message = issues.length ? [...new Set(issues)].join(' ') : error?.message || message
    }
    throw new OperationalApiError(message, response.status)
  }
  if (!payload || typeof payload !== 'object' || !('status' in payload) || payload.status !== 'success' || !('data' in payload)) {
    throw new OperationalApiError('El servidor devolvió una respuesta inesperada.')
  }
  return payload as T
}
