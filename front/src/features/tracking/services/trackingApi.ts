import type {
  PickupOptions,
  PickupOptionsSuccessResponse,
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
  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'
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
    deliveryType: trackingResponse.data.tipo_entrega === 'sucursal' ? 'sucursal' : 'domicilio',
    destination: trackingResponse.data.destino,
    latitude: trackingResponse.data.latitud_destino ?? null,
    longitude: trackingResponse.data.longitud_destino ?? null,
    packages: trackingResponse.data.paquetes.map((shipmentPackage) => ({
      packageNumber: shipmentPackage.numero_paquete,
      status: shipmentPackage.estado,
      description: shipmentPackage.descripcion,
      notes: shipmentPackage.observaciones,
      registeredAt: shipmentPackage.fecha_registro,
      updatedAt: shipmentPackage.ultima_actualizacion,
      history: (shipmentPackage.historial ?? []).map((event) => ({ previousStatus: event.estado_anterior, status: event.estado, occurredAt: event.fecha_hora, description: event.descripcion })),
      driverLocation: shipmentPackage.ubicacion_repartidor ? {
        latitude: shipmentPackage.ubicacion_repartidor.latitud, longitude: shipmentPackage.ubicacion_repartidor.longitud, updatedAt: shipmentPackage.ubicacion_repartidor.actualizado_at,
      } : null,
      pickup: shipmentPackage.retiro ? {
        branch: shipmentPackage.retiro.sucursal, address: shipmentPackage.retiro.direccion,
        until: shipmentPackage.retiro.hasta, pickedUpBy: shipmentPackage.retiro.lo_retira,
      } : null,
      failedVisits: shipmentPackage.visitas_fallidas ?? 0,
      maxVisits: shipmentPackage.max_visitas ?? 2,
      isReturn: Boolean(shipmentPackage.en_devolucion),
    })),
  }
}

export async function getPickupOptions(token: string, signal?: AbortSignal): Promise<PickupOptions> {
  if (!apiUrl) throw new TrackingApiError('No se configuró la URL de la API.')
  let response: Response
  try {
    response = await fetch(`${apiUrl}/sucursales/opciones-retiro/${encodeURIComponent(token)}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new TrackingApiError('No pudimos consultar la sucursal de retiro. Intentá nuevamente.')
  }
  const payload = await readJson(response)
  if (!response.ok) throw new TrackingApiError(getErrorMessage(payload, response.status), response.status)

  const options = payload as PickupOptionsSuccessResponse
  if (options?.status !== 'success' || typeof options.data?.aplica_retiro !== 'boolean' || !Array.isArray(options.data.paquetes)) {
    throw new TrackingApiError('El servidor devolvió una respuesta inesperada.')
  }
  const branch = options.data.sucursal_asignada
  return {
    applies: options.data.aplica_retiro,
    reason: options.data.motivo_no_aplica,
    branch: branch ? {
      name: branch.nombre, address: branch.direccion, city: branch.ciudad, province: branch.provincia,
      latitude: branch.latitud, longitude: branch.longitud,
    } : null,
    packages: options.data.paquetes.map((item) => ({ packageNumber: item.numero_paquete, ready: item.disponible_para_retirar })),
    requirements: {
      recipient: options.data.requisitos_retiro?.titular ?? '',
      authorizedPerson: options.data.requisitos_retiro?.tercero_autorizado ?? '',
    },
  }
}
