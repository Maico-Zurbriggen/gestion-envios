import type {
  ShipmentTracking,
  TrackingSuccessResponse,
} from '../types/tracking.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

interface ApiErrorPayload {
  detail?: Array<{ msg?: string }> | string
  message?: string
  errors?: Array<{ message?: string }>
}

export class TrackingApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'TrackingApiError'
    this.status = status
  }
}

function getErrorMessage(payload: unknown, status: number) {
  if (payload && typeof payload === 'object') {
    const { detail, errors, message } = payload as ApiErrorPayload

    if (Array.isArray(errors)) {
      const messages = errors
        .map((issue) => issue.message)
        .filter((issue): issue is string => Boolean(issue))
      if (messages.length) return messages.join('. ')
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((issue) => issue.msg)
        .filter((issue): issue is string => Boolean(issue))
      if (messages.length) return messages.join('. ')
    }

    if (typeof detail === 'string' && detail) return detail
    if (typeof message === 'string' && message) return message
  }

  if (status === 404) return 'No encontramos un envío asociado a ese código.'
  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'
  return 'No pudimos consultar el seguimiento. Revisá el código ingresado.'
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function getShipmentTracking(
  token: string,
): Promise<ShipmentTracking> {
  if (!apiUrl) throw new TrackingApiError('No se configuró la URL de la API.')

  let response: Response

  try {
    response = await fetch(`${apiUrl}/seguimiento/${encodeURIComponent(token)}`, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new TrackingApiError(
      'No pudimos conectarnos con el servidor. Intentá nuevamente.',
    )
  }

  const payload = await readJson(response)
  if (!response.ok) {
    throw new TrackingApiError(
      getErrorMessage(payload, response.status),
      response.status,
    )
  }

  const trackingResponse = payload as TrackingSuccessResponse
  if (
    trackingResponse?.status !== 'success' ||
    !trackingResponse.data?.token_seguimiento ||
    !Array.isArray(trackingResponse.data.paquetes)
  ) {
    throw new TrackingApiError('El servidor devolvió una respuesta inesperada.')
  }

  return {
    trackingToken: trackingResponse.data.token_seguimiento,
    destination: trackingResponse.data.destino,
    packages: trackingResponse.data.paquetes.map((shipmentPackage) => ({
      packageNumber: shipmentPackage.numero_paquete,
      status: shipmentPackage.estado,
      description: shipmentPackage.descripcion,
      notes: shipmentPackage.observaciones,
      registeredAt: shipmentPackage.fecha_registro,
      updatedAt: shipmentPackage.ultima_actualizacion,
    })),
  }
}
