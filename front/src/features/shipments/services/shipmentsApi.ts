import type {
  ApiBranch,
  ApiCreatedPackage,
  Branch,
  BranchesSuccessResponse,
  CreatedPackage,
  CreatedShipment,
  CreateShipmentInput,
  CreateShipmentSuccessResponse,
} from '../types/shipment.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

interface ApiErrorPayload {
  detail?: Array<{ msg?: string; loc?: Array<string | number> }> | string
  message?: string
  errors?: Array<{ field?: string; message?: string }>
}

export class ShipmentsApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ShipmentsApiError'
  }
}

function mapBranch(branch: ApiBranch): Branch {
  return {
    id: branch.id,
    name: branch.nombre,
    province: branch.provincia,
    city: branch.ciudad,
    address: branch.direccion,
    latitude: branch.latitud,
    longitude: branch.longitud,
  }
}

function mapPackage(shipmentPackage: ApiCreatedPackage): CreatedPackage {
  return {
    id: shipmentPackage.id,
    packageNumber: shipmentPackage.numero_paquete,
    description: shipmentPackage.descripcion,
    weightKg: shipmentPackage.peso_kg,
    lengthCm: shipmentPackage.largo_cm,
    widthCm: shipmentPackage.ancho_cm,
    heightCm: shipmentPackage.alto_cm,
    notes: shipmentPackage.observaciones,
    status: shipmentPackage.estado,
  }
}

function mapShipment(response: CreateShipmentSuccessResponse): CreatedShipment {
  const shipment = response.data

  return {
    id: shipment.id,
    trackingToken: shipment.token_seguimiento,
    senderName: shipment.remitente_nombre,
    senderDocument: shipment.remitente_documento,
    senderPhone: shipment.remitente_telefono,
    senderEmail: shipment.remitente_email,
    recipientName: shipment.destinatario_nombre,
    recipientPhone: shipment.destinatario_telefono,
    recipientEmail: shipment.destinatario_email,
    deliveryType: shipment.tipo_entrega,
    destinationProvince: shipment.provincia_destino,
    destinationCity: shipment.ciudad_destino,
    destinationAddress: shipment.direccion_destino,
    destinationLatitude: shipment.latitud_destino,
    destinationLongitude: shipment.longitud_destino,
    destinationBranch: shipment.sucursal_destino
      ? mapBranch(shipment.sucursal_destino)
      : null,
    packages: shipment.paquetes.map(mapPackage),
    createdAt: shipment.created_at,
  }
}

function getErrorMessage(payload: unknown, status: number, operation: string) {
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

  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'
  return `No pudimos ${operation}. Revisá los datos ingresados.`
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function getBranches(): Promise<Branch[]> {
  if (!apiUrl) throw new ShipmentsApiError('No se configuró la URL de la API.')

  let response: Response

  try {
    response = await fetch(`${apiUrl}/sucursales`, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new ShipmentsApiError(
      'No pudimos conectarnos con el servidor para obtener las sucursales.',
    )
  }

  const payload = await readJson(response)
  if (!response.ok) {
    throw new ShipmentsApiError(
      getErrorMessage(payload, response.status, 'obtener las sucursales'),
    )
  }

  const branchesResponse = payload as BranchesSuccessResponse
  if (
    branchesResponse?.status !== 'success' ||
    !Array.isArray(branchesResponse.data)
  ) {
    throw new ShipmentsApiError('El servidor devolvió una respuesta inesperada.')
  }

  return branchesResponse.data.map(mapBranch)
}

export async function createShipment(
  input: CreateShipmentInput,
): Promise<CreatedShipment> {
  if (!apiUrl) throw new ShipmentsApiError('No se configuró la URL de la API.')

  let response: Response

  try {
    response = await fetch(`${apiUrl}/envios`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        remitente_nombre: input.senderName,
        remitente_documento: input.senderDocument,
        remitente_telefono: input.senderPhone,
        remitente_email: input.senderEmail,
        destinatario_nombre: input.recipientName,
        destinatario_telefono: input.recipientPhone,
        destinatario_email: input.recipientEmail,
        tipo_entrega: input.deliveryType,
        provincia_destino: input.destinationProvince,
        ciudad_destino: input.destinationCity,
        direccion_destino: input.destinationAddress,
        latitud_destino: input.destinationLatitude,
        longitud_destino: input.destinationLongitude,
        sucursal_destino_id: input.destinationBranchId,
        terminos_aceptados: input.termsAccepted,
        paquetes: input.packages.map((shipmentPackage) => ({
          descripcion: shipmentPackage.description,
          peso_kg: shipmentPackage.weightKg,
          largo_cm: shipmentPackage.lengthCm,
          ancho_cm: shipmentPackage.widthCm,
          alto_cm: shipmentPackage.heightCm,
          observaciones: shipmentPackage.notes,
        })),
      }),
    })
  } catch {
    throw new ShipmentsApiError(
      'No pudimos conectarnos con el servidor. Intentá nuevamente.',
    )
  }

  const payload = await readJson(response)
  if (!response.ok) {
    throw new ShipmentsApiError(
      getErrorMessage(payload, response.status, 'registrar el envío'),
    )
  }

  const shipmentResponse = payload as CreateShipmentSuccessResponse
  if (shipmentResponse?.status !== 'success' || !shipmentResponse.data) {
    throw new ShipmentsApiError('El servidor devolvió una respuesta inesperada.')
  }

  return mapShipment(shipmentResponse)
}
